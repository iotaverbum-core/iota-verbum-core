from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_CHAT_COMPLETIONS_PATH = "/chat/completions"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-pro"
DEFAULT_DEEPSEEK_FALLBACK_MODEL = "deepseek-v4-flash"

SYSTEM_PROMPT = (
    "You are a deterministic evidence-revision analyst. "
    "Use only claims and artifact IDs present in the packs. "
    "Revise only what changed. "
    "Preserve stable sibling branches unless new contrary evidence is introduced. "
    "Track newly created or resolved unknowns explicitly. "
    "Never invent evidence citations. Return JSON only."
)

REVISION_DELTA_INSTRUCTIONS = """\
Return exactly one JSON object matching this RevisionDelta shape:
{
  "schema_version": "1.0.0",
  "changed_edges": [
    {
      "id": "edge:...",
      "change_type": "added|modified|strengthened|weakened|removed",
      "before": null,
      "after": {},
      "source_op_ids": ["op:..."]
    }
  ],
  "changed_events": [],
  "changed_states": [],
  "forbidden_revisions": ["state:..."],
  "new_conflicts": [],
  "new_unknowns": [
    {
      "id": "unknown:...",
      "change_type": "added",
      "before": null,
      "after": {},
      "source_op_ids": ["op:..."]
    }
  ],
  "preserved_items": ["state:..."],
  "pruned_conflicts": [],
  "resolved_unknowns": [
    {
      "id": "unknown:...",
      "change_type": "resolved",
      "before": {},
      "after": {},
      "source_op_ids": ["op:..."]
    }
  ],
  "scenario_rank_changes": [
    {
      "scenario_id": "scenario:...",
      "before_rank": 2,
      "after_rank": 1
    }
  ],
  "supporting_evidence_map": {"state:...": ["evidence:..."]},
  "must_preserve_claims": ["state:..."],
  "must_revise_claims": ["state:..."],
  "named_evidence_artifact": "literal artifact label or evidence:...",
  "preservation_notes": "string",
  "revision_notes": "string",
  "structural_invariant": "string"
}

Rules:
- Use canonical state:, event:, edge:, scenario:, unknown:, and evidence: IDs.
- Every item in changed_edges, changed_events, changed_states, new_unknowns,
  and resolved_unknowns must be an object with id, change_type, before, after,
  and source_op_ids fields. Never emit a bare string in those lists.
- source_op_ids must contain only operation IDs explicitly present in the prompt.
  If no op: IDs are present, use []. Never invent op: IDs. Never put evidence:
  IDs in source_op_ids; evidence IDs belong in evidence_ids and
  supporting_evidence_map.
- Include before and after records only for items that changed.
- For before and after records, copy the full changed object when available, not
  only the changed scalar fields.
- Include every changed item in supporting_evidence_map. That includes changed
  states, changed edges, resolved unknowns, and any changed scenarios.
- Compare clean and perturbed scenarios by scenario_id. If rank, status, basis,
  or live ordering changes, add one scenario_rank_changes object for every
  affected scenario. Use keys exactly scenario_id, before_rank, and after_rank.
  Never use id, old_rank, or new_rank for scenario rank changes. For a newly
  introduced scenario, use before_rank: null.
- When a resolved unknown is resolved by new corroborating evidence, include both
  the prior evidence and corroborating evidence in its after.evidence_ids and in
  supporting_evidence_map.
- If a live scenario remains semantically supported by the revised claim, include
  that scenario ID in supporting_evidence_map with the revised claim evidence.
- named_evidence_artifact is a literal metadata value, not necessarily an
  evidence: ID. If sections.metadata.named_evidence_artifact appears in either
  pack, copy that string exactly.
- preserved_items and forbidden_revisions must include all stable sibling state:,
  edge:, and unknown: IDs that should not be revised, not just state IDs.
- Every ID in forbidden_revisions must also appear in preserved_items.
- structural_invariant must be a non-empty sentence explaining the under-revision
  and over-revision failure modes for this case.
- Do not rewrite preserved sibling branches.
- Do not add commentary, markdown, or text outside the JSON object.
"""


class RevisionChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    change_type: str
    before: Any = None
    after: Any = None
    source_op_ids: list[str] = Field(default_factory=list)


class RevisionDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    changed_edges: list[RevisionChange]
    changed_events: list[RevisionChange]
    changed_states: list[RevisionChange]
    forbidden_revisions: list[str]
    new_conflicts: list[dict[str, Any]]
    new_unknowns: list[RevisionChange]
    preserved_items: list[str]
    pruned_conflicts: list[dict[str, Any]]
    resolved_unknowns: list[RevisionChange]
    scenario_rank_changes: list[dict[str, Any]]
    supporting_evidence_map: dict[str, list[str]]
    must_preserve_claims: list[str]
    must_revise_claims: list[str]
    named_evidence_artifact: str
    preservation_notes: str
    revision_notes: str
    structural_invariant: str

    def to_canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class SealedFailureArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["iv.cuc_harness.sealed_failure.v1"]
    failure_id: str
    provider: Literal["deepseek", "claude"]
    model: str
    endpoint: str
    error_type: str
    message: str
    status_code: int | None = None
    response_body: Any = None

    def to_canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class DeepSeekProposer:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
        base_url: str = DEEPSEEK_BASE_URL,
        timeout_seconds: float = 90.0,
        strict_copy: bool = False,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY")
        self.model = model or os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)
        if fallback_model is not None:
            self.fallback_model = fallback_model
        else:
            env_fallback_model = os.getenv("DEEPSEEK_FALLBACK_MODEL")
            self.fallback_model = (
                env_fallback_model
                if env_fallback_model is not None
                else DEFAULT_DEEPSEEK_FALLBACK_MODEL
            )
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.strict_copy = strict_copy
        self.client = client

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}{DEEPSEEK_CHAT_COMPLETIONS_PATH}"

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
                message="DEEPSEEK_API_KEY is not set.",
            )

        messages = self._build_messages(
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
            result = self._request_delta(model=model, messages=messages)
            if isinstance(result, RevisionDelta):
                return result
            last_failure = result
        if last_failure is not None:
            return last_failure
        return self._failure(
            model=self.model,
            error_type="internal_error",
            message="No DeepSeek request attempt was made.",
        )

    def _build_messages(
        self,
        *,
        clean_pack: Mapping[str, Any] | str,
        perturbed_pack: Mapping[str, Any] | str,
        case_id: str,
        strict_copy: bool,
    ) -> list[dict[str, str]]:
        copy_rule = (
            "STRICT_COPY=1. Copy unchanged scalar field values exactly when a "
            "changed record needs before/after context."
            if strict_copy
            else "STRICT_COPY=0. Do not copy the whole pack; emit only the "
            "minimal changed before/after records needed for the delta."
        )
        user_prompt = "\n\n".join(
            [
                f"CASE_ID: {case_id or '(unspecified)'}",
                copy_rule,
                REVISION_DELTA_INSTRUCTIONS,
                "CLEAN_PACK:",
                _format_pack(clean_pack),
                "PERTURBED_PACK:",
                _format_pack(perturbed_pack),
            ]
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _request_delta(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
    ) -> RevisionDelta | SealedFailureArtifact:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 1.0,
            "top_p": 1.0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self._post(payload, headers)
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
            return self._failure(
                model=model,
                error_type="api_error",
                message=f"DeepSeek API returned HTTP {status_code}.",
                status_code=status_code,
                response_body=response_body,
            )

        try:
            content_obj = _extract_json_content(response_body)
            content_obj = _normalize_revision_delta_payload(content_obj)
            return RevisionDelta.model_validate(content_obj)
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            return self._failure(
                model=model,
                error_type=exc.__class__.__name__,
                message=str(exc),
                status_code=status_code,
                response_body=response_body,
            )

    def _post(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response:
        if self.client is not None:
            return self.client.post(self.endpoint, headers=headers, json=payload)
        with httpx.Client(timeout=self.timeout_seconds) as client:
            return client.post(self.endpoint, headers=headers, json=payload)

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
            "provider": "deepseek",
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


def _format_pack(pack: Mapping[str, Any] | str) -> str:
    if isinstance(pack, str):
        return pack
    return json.dumps(
        pack,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _extract_json_content(response_body: Any) -> dict[str, Any]:
    if not isinstance(response_body, Mapping):
        raise TypeError("DeepSeek response body is not a JSON object.")
    choices = response_body["choices"]
    if not isinstance(choices, list) or not choices:
        raise ValueError("DeepSeek response did not include any choices.")
    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise TypeError("DeepSeek choice is not a JSON object.")
    message = first_choice.get("message", {})
    if not isinstance(message, Mapping):
        raise TypeError("DeepSeek message is not a JSON object.")
    content = message.get("content")
    if isinstance(content, Mapping):
        return dict(content)
    if not isinstance(content, str):
        raise TypeError("DeepSeek message content is not a JSON string.")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise TypeError("DeepSeek message content is not a JSON object.")
    return parsed


def _normalize_revision_delta_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    for field_name in (
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
    ):
        normalized.setdefault(field_name, [])
    normalized.setdefault("supporting_evidence_map", {})
    for field_name, default_change_type in (
        ("changed_edges", "modified"),
        ("changed_events", "modified"),
        ("changed_states", "modified"),
        ("new_unknowns", "added"),
        ("resolved_unknowns", "resolved"),
    ):
        normalized[field_name] = _normalize_change_list(
            normalized.get(field_name, []),
            default_change_type=default_change_type,
        )
    normalized["scenario_rank_changes"] = _normalize_scenario_rank_changes(
        normalized.get("scenario_rank_changes", []),
    )
    normalized["preserved_items"] = _merge_unique_string_lists(
        normalized.get("preserved_items", []),
        normalized.get("forbidden_revisions", []),
    )
    return normalized


def _normalize_change_list(value: Any, *, default_change_type: str) -> list[Any]:
    if not isinstance(value, list):
        return value
    normalized_items: list[Any] = []
    for item in value:
        if isinstance(item, str):
            normalized_items.append(
                {
                    "id": item,
                    "change_type": default_change_type,
                    "before": None,
                    "after": None,
                    "source_op_ids": [],
                }
            )
            continue
        normalized_items.append(item)
    return normalized_items


def _normalize_scenario_rank_changes(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return value
    normalized_items: list[Any] = []
    for item in value:
        if not isinstance(item, Mapping):
            normalized_items.append(item)
            continue
        normalized_item = dict(item)
        if "scenario_id" not in normalized_item and isinstance(
            normalized_item.get("id"),
            str,
        ):
            normalized_item["scenario_id"] = normalized_item.pop("id")
        else:
            normalized_item.pop("id", None)
        if "before_rank" not in normalized_item and "old_rank" in normalized_item:
            normalized_item["before_rank"] = normalized_item.pop("old_rank")
        else:
            normalized_item.pop("old_rank", None)
        if "after_rank" not in normalized_item and "new_rank" in normalized_item:
            normalized_item["after_rank"] = normalized_item.pop("new_rank")
        else:
            normalized_item.pop("new_rank", None)
        normalized_items.append(normalized_item)
    return normalized_items


def _merge_unique_string_lists(first: Any, second: Any) -> Any:
    if not isinstance(first, list) or not isinstance(second, list):
        return first
    merged: list[str] = []
    seen: set[str] = set()
    for value in [*first, *second]:
        if not isinstance(value, str) or value in seen:
            continue
        merged.append(value)
        seen.add(value)
    return merged


__all__ = [
    "DeepSeekProposer",
    "RevisionChange",
    "RevisionDelta",
    "SealedFailureArtifact",
    "_normalize_revision_delta_payload",
]
