from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections.abc import Mapping
from typing import Any, Callable

import httpx
from pydantic import ValidationError

from core.cuc_harness.deepseek_proposer import (
    REVISION_DELTA_INSTRUCTIONS,
    SYSTEM_PROMPT,
    RevisionDelta,
    SealedFailureArtifact,
    _canonical_json,
    _format_pack,
    _normalize_revision_delta_payload,
)

CLAUDE_BASE_URL = "https://api.anthropic.com"
CLAUDE_MESSAGES_PATH = "/v1/messages"
CLAUDE_API_VERSION = "2023-06-01"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_CLAUDE_FALLBACK_MODEL = ""
DEFAULT_CLAUDE_MAX_TOKENS = 8192
DEFAULT_CLAUDE_RATE_LIMIT_RETRIES = 5
DEFAULT_CLAUDE_RATE_LIMIT_SLEEP_SECONDS = 70.0
CLAUDE_REVISION_DELTA_TOOL_NAME = "emit_revision_delta"

CLAUDE_SCHEMA_COMPATIBILITY_INSTRUCTIONS = """\
Claude structured-output compatibility rules:
- before and after are strings in the API schema. Encode each value as compact
  JSON text: use "null" for no value, "{}" for an empty object, and a full JSON
  object string when before/after record context is available.
- supporting_evidence_map is a string in the API schema. Encode it as compact
  JSON object text mapping canonical IDs to evidence ID arrays, for example:
  {"state:primary":["evidence:primary"]}. Include only relevant IDs.
"""

CLAUDE_REVISION_PRECISION_INSTRUCTIONS = """\
Claude RevisionDelta precision rules:
- Treat background/admin branches as context, not preserved sibling claims, when
  IDs or attributes indicate background_branch, supports_background_context,
  state:bg_, edge:bg_, unknown:bg_, event:bg_, or scenario:bg_.
- Do not include background/admin IDs in changed_* lists unless the revise_focus
  branch directly depends on the changed value.
- For no-op cases where metadata.revise_focus is empty or no substantive claim
  changed, include all unchanged state:, edge:, and unknown: IDs in both
  preserved_items and forbidden_revisions, including background IDs.
- For localized revision cases, preserved_items and forbidden_revisions should
  include metadata.preserve_focus branches and their directly associated edge
  and unknown IDs. Add background IDs there only when metadata.preserve_focus
  explicitly names them or the case explicitly says background context must be
  preserved as a scored branch.
- must_preserve_claims should name claim/state IDs only; do not add background
  state IDs there unless metadata.preserve_focus names them.
- changed_events should include only events that materially drive a changed
  claim, scenario rank change, or unknown resolution. Ignore background/admin
  timestamp drift when it does not change the target branch under revise_focus.
- For resolved unknowns, use status "resolved" and resolution_value when a
  resolution value is needed. Do not use status "closed" or a "resolution" key
  unless those exact fields are present in a source record.
- Compare scenario rank changes by scenario_id. Emit one record per affected
  scenario; the array order is not semantically important.
"""

REVISION_DELTA_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string"},
        "changed_edges": {"type": "array", "items": {"$ref": "#/$defs/change"}},
        "changed_events": {"type": "array", "items": {"$ref": "#/$defs/change"}},
        "changed_states": {"type": "array", "items": {"$ref": "#/$defs/change"}},
        "forbidden_revisions": {"type": "array", "items": {"type": "string"}},
        "new_conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
            },
        },
        "new_unknowns": {"type": "array", "items": {"$ref": "#/$defs/change"}},
        "preserved_items": {"type": "array", "items": {"type": "string"}},
        "pruned_conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
            },
        },
        "resolved_unknowns": {"type": "array", "items": {"$ref": "#/$defs/change"}},
        "scenario_rank_changes": {
            "type": "array",
            "items": {"$ref": "#/$defs/scenario_rank_change"},
        },
        "supporting_evidence_map": {"type": "string"},
        "must_preserve_claims": {"type": "array", "items": {"type": "string"}},
        "must_revise_claims": {"type": "array", "items": {"type": "string"}},
        "named_evidence_artifact": {"type": "string"},
        "preservation_notes": {"type": "string"},
        "revision_notes": {"type": "string"},
        "structural_invariant": {"type": "string"},
    },
    "required": [
        "schema_version",
        "changed_edges",
        "changed_events",
        "changed_states",
        "forbidden_revisions",
        "new_conflicts",
        "new_unknowns",
        "preserved_items",
        "pruned_conflicts",
        "resolved_unknowns",
        "scenario_rank_changes",
        "supporting_evidence_map",
        "must_preserve_claims",
        "must_revise_claims",
        "named_evidence_artifact",
        "preservation_notes",
        "revision_notes",
        "structural_invariant",
    ],
    "additionalProperties": False,
    "$defs": {
        "change": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "change_type": {"type": "string"},
                "before": {"type": "string"},
                "after": {"type": "string"},
                "source_op_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["id", "change_type", "before", "after", "source_op_ids"],
            "additionalProperties": False,
        },
        "scenario_rank_change": {
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string"},
                "before_rank": {"type": ["integer", "null"]},
                "after_rank": {"type": "integer"},
            },
            "required": ["scenario_id", "before_rank", "after_rank"],
            "additionalProperties": False,
        },
    },
}


class ClaudeProposer:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
        base_url: str = CLAUDE_BASE_URL,
        timeout_seconds: float = 90.0,
        max_tokens: int | None = None,
        effort: str | None = None,
        strict_copy: bool = False,
        client: httpx.Client | None = None,
        rate_limit_retries: int = DEFAULT_CLAUDE_RATE_LIMIT_RETRIES,
        rate_limit_sleep_seconds: float = DEFAULT_CLAUDE_RATE_LIMIT_SLEEP_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = (
            api_key
            if api_key is not None
            else os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        )
        self.model = model or os.getenv("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL)
        if fallback_model is not None:
            self.fallback_model = fallback_model
        else:
            env_fallback_model = os.getenv("CLAUDE_FALLBACK_MODEL")
            self.fallback_model = (
                env_fallback_model
                if env_fallback_model is not None
                else DEFAULT_CLAUDE_FALLBACK_MODEL
            )
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens or int(
            os.getenv("CLAUDE_MAX_TOKENS", str(DEFAULT_CLAUDE_MAX_TOKENS))
        )
        self.effort = effort if effort is not None else os.getenv("CLAUDE_EFFORT")
        self.strict_copy = strict_copy
        self.client = client
        self.rate_limit_retries = max(0, int(rate_limit_retries))
        self.rate_limit_sleep_seconds = float(rate_limit_sleep_seconds)
        self.sleep = sleep

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}{CLAUDE_MESSAGES_PATH}"

    def propose(
        self,
        clean_pack: Mapping[str, Any] | str,
        perturbed_pack: Mapping[str, Any] | str,
        *,
        case_id: str = "",
        strict_copy: bool | None = None,
    ) -> RevisionDelta | SealedFailureArtifact:
        if not self.api_key:
            return self._failure(
                model=self.model,
                error_type="missing_api_key",
                message="ANTHROPIC_API_KEY or CLAUDE_API_KEY is not set.",
            )

        user_prompt = self._build_user_prompt(
            clean_pack=clean_pack,
            perturbed_pack=perturbed_pack,
            case_id=case_id,
            strict_copy=self.strict_copy if strict_copy is None else strict_copy,
        )
        models = [self.model]
        if self.fallback_model and self.fallback_model not in models:
            models.append(self.fallback_model)

        last_failure: SealedFailureArtifact | None = None
        for model in models:
            result = self._request_delta(
                model=model,
                user_prompt=user_prompt,
            )
            if isinstance(result, RevisionDelta):
                return result
            last_failure = result
        if last_failure is not None:
            return last_failure
        return self._failure(
            model=self.model,
            error_type="internal_error",
            message="No Claude request attempt was made.",
        )

    def _build_user_prompt(
        self,
        *,
        clean_pack: Mapping[str, Any] | str,
        perturbed_pack: Mapping[str, Any] | str,
        case_id: str,
        strict_copy: bool,
    ) -> str:
        copy_rule = (
            "STRICT_COPY=1. Copy unchanged scalar field values exactly when a "
            "changed record needs before/after context."
            if strict_copy
            else "STRICT_COPY=0. Do not copy the whole pack; emit only the "
            "minimal changed before/after records needed for the delta."
        )
        return "\n\n".join(
            [
                f"CASE_ID: {case_id or '(unspecified)'}",
                copy_rule,
                REVISION_DELTA_INSTRUCTIONS,
                CLAUDE_SCHEMA_COMPATIBILITY_INSTRUCTIONS,
                CLAUDE_REVISION_PRECISION_INSTRUCTIONS,
                "CLEAN_PACK:",
                _format_pack(clean_pack),
                "PERTURBED_PACK:",
                _format_pack(perturbed_pack),
            ]
        )

    def _request_delta(
        self,
        *,
        model: str,
        user_prompt: str,
    ) -> RevisionDelta | SealedFailureArtifact:
        payload = self._structured_output_payload(model=model, user_prompt=user_prompt)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": CLAUDE_API_VERSION,
            "content-type": "application/json",
        }
        try:
            response = self._post_with_rate_limit_retry(payload, headers)
        except httpx.HTTPError as exc:
            return self._failure(
                model=model,
                error_type=exc.__class__.__name__,
                message=str(exc),
            )

        status_code = response.status_code
        try:
            response_body: Any = response.json()
        except ValueError:
            response_body = response.text

        if status_code >= 400:
            if _should_retry_with_tool_schema(response_body, status_code):
                tool_payload = self._tool_schema_payload(
                    model=model,
                    user_prompt=user_prompt,
                )
                try:
                    response = self._post_with_rate_limit_retry(
                        tool_payload,
                        headers,
                    )
                except httpx.HTTPError as exc:
                    return self._failure(
                        model=model,
                        error_type=exc.__class__.__name__,
                        message=str(exc),
                    )
                status_code = response.status_code
                try:
                    response_body = response.json()
                except ValueError:
                    response_body = response.text

        if status_code >= 400:
            return self._failure(
                model=model,
                error_type="api_error",
                message=f"Claude API returned HTTP {status_code}.",
                status_code=status_code,
                response_body=response_body,
            )

        try:
            content_obj = _extract_claude_json_content(response_body)
            content_obj = _normalize_revision_delta_payload(content_obj)
            content_obj = hydrate_revision_delta_json_fields(content_obj)
            return RevisionDelta.model_validate(content_obj)
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            return self._failure(
                model=model,
                error_type=exc.__class__.__name__,
                message=str(exc),
                status_code=status_code,
                response_body=response_body,
            )

    def _base_payload(self, *, model: str, user_prompt: str) -> dict[str, Any]:
        return {
            "model": model,
            "max_tokens": self.max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }

    def _structured_output_payload(
        self,
        *,
        model: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        payload = self._base_payload(model=model, user_prompt=user_prompt)
        payload["output_config"] = {
            "format": {
                "type": "json_schema",
                "schema": REVISION_DELTA_JSON_SCHEMA,
            }
        }
        if self.effort:
            payload["output_config"]["effort"] = self.effort
        return payload

    def _tool_schema_payload(
        self,
        *,
        model: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        payload = self._base_payload(model=model, user_prompt=user_prompt)
        payload["tools"] = [
            {
                "name": CLAUDE_REVISION_DELTA_TOOL_NAME,
                "description": "Emit exactly one structured RevisionDelta object.",
                "strict": True,
                "input_schema": REVISION_DELTA_JSON_SCHEMA,
            }
        ]
        payload["tool_choice"] = {
            "type": "tool",
            "name": CLAUDE_REVISION_DELTA_TOOL_NAME,
        }
        return payload

    def _post(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        if self.client is not None:
            return self.client.post(self.endpoint, headers=headers, json=payload)
        with httpx.Client(timeout=self.timeout_seconds) as client:
            return client.post(self.endpoint, headers=headers, json=payload)

    def _post_with_rate_limit_retry(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        for attempt in range(self.rate_limit_retries + 1):
            response = self._post(payload, headers)
            if response.status_code == 429 and attempt < self.rate_limit_retries:
                sleep_seconds = _retry_after_seconds(
                    response,
                    default_seconds=self.rate_limit_sleep_seconds,
                )
                print(
                    "Claude API rate limited; "
                    f"sleeping {sleep_seconds:g}s before retry "
                    f"{attempt + 1}/{self.rate_limit_retries}.",
                    file=sys.stderr,
                )
                self.sleep(sleep_seconds)
                continue
            return response
        return response

    def _failure(
        self,
        *,
        model: str,
        error_type: str,
        message: str,
        status_code: int | None = None,
        response_body: Any = None,
    ) -> SealedFailureArtifact:
        payload = {
            "schema_version": "iv.cuc_harness.sealed_failure.v1",
            "provider": "claude",
            "model": model,
            "endpoint": self.endpoint,
            "error_type": error_type,
            "message": message,
            "status_code": status_code,
            "response_body": response_body,
        }
        failure_id = "sealed-failure:" + hashlib.sha256(
            _canonical_json(payload).encode("utf-8")
        ).hexdigest()
        return SealedFailureArtifact(failure_id=failure_id, **payload)


def _extract_claude_json_content(response_body: Any) -> dict[str, Any]:
    if not isinstance(response_body, Mapping):
        raise TypeError("Claude response body is not a JSON object.")
    content = response_body["content"]
    if not isinstance(content, list) or not content:
        raise ValueError("Claude response did not include any content blocks.")
    for block in content:
        if not isinstance(block, Mapping):
            continue
        if (
            block.get("type") == "tool_use"
            and block.get("name") == CLAUDE_REVISION_DELTA_TOOL_NAME
            and isinstance(block.get("input"), Mapping)
        ):
            return dict(block["input"])
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, Mapping):
            return dict(text)
        if isinstance(text, str):
            parsed = json.loads(text)
            if not isinstance(parsed, dict):
                raise TypeError("Claude text content is not a JSON object.")
            return parsed
    raise ValueError("Claude response did not include a text JSON content block.")


def _retry_after_seconds(response: httpx.Response, *, default_seconds: float) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            parsed = float(retry_after)
        except ValueError:
            return default_seconds
        return max(0.0, parsed)
    return default_seconds


def _should_retry_with_tool_schema(response_body: Any, status_code: int) -> bool:
    if status_code not in {400, 422}:
        return False
    if isinstance(response_body, str):
        serialized = response_body
    else:
        try:
            serialized = _canonical_json(response_body)
        except (TypeError, ValueError):
            serialized = str(response_body)
    lowered = serialized.lower()
    return any(
        marker in lowered
        for marker in (
            "output_config",
            "output_format",
            "json_schema",
            "format",
        )
    )


def hydrate_revision_delta_json_fields(payload: dict[str, Any]) -> dict[str, Any]:
    hydrated = dict(payload)
    hydrated["supporting_evidence_map"] = _hydrate_json_string(
        hydrated.get("supporting_evidence_map", {})
    )
    for field_name in (
        "changed_edges",
        "changed_events",
        "changed_states",
        "new_unknowns",
        "resolved_unknowns",
    ):
        hydrated[field_name] = _hydrate_change_list(hydrated.get(field_name, []))
    return hydrated


def _hydrate_change_list(value: Any) -> Any:
    if not isinstance(value, list):
        return value
    hydrated_items: list[Any] = []
    for item in value:
        if not isinstance(item, Mapping):
            hydrated_items.append(item)
            continue
        hydrated_item = dict(item)
        for field_name in ("before", "after"):
            if field_name in hydrated_item:
                hydrated_item[field_name] = _hydrate_json_string(
                    hydrated_item[field_name]
                )
        hydrated_items.append(hydrated_item)
    return hydrated_items


def _hydrate_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped == "":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


__all__ = [
    "CLAUDE_API_VERSION",
    "CLAUDE_BASE_URL",
    "CLAUDE_REVISION_DELTA_TOOL_NAME",
    "ClaudeProposer",
    "DEFAULT_CLAUDE_MODEL",
    "REVISION_DELTA_JSON_SCHEMA",
    "hydrate_revision_delta_json_fields",
    "_extract_claude_json_content",
]
