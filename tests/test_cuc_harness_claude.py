from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

from core.cuc_harness.claude_proposer import (
    CLAUDE_REVISION_DELTA_TOOL_NAME,
    DEFAULT_CLAUDE_MODEL,
    REVISION_DELTA_JSON_SCHEMA,
    ClaudeProposer,
    _extract_claude_json_content,
    hydrate_revision_delta_json_fields,
)
from core.cuc_harness.deepseek_proposer import RevisionDelta, SealedFailureArtifact
from core.determinism.canonical_json import dumps_canonical
from core.determinism.finalize import finalize
from core.determinism.ledger import write_run

CASE_ID = "CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
SOURCE_CASE_ID = "CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
FIXTURE_DIR = Path("benchmark/kaggle/fixtures") / SOURCE_CASE_ID
EVIDENCE_BUNDLE_PATH = Path("tests/fixtures/evidence_bundle_example.json")


@pytest.mark.skipif(
    not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")),
    reason=(
        "ANTHROPIC_API_KEY or CLAUDE_API_KEY is required for the live "
        "Claude proposer test."
    ),
)
def test_claude_proposer_on_simple_cuc_case(tmp_path: Path) -> None:
    clean_pack = _read_json(FIXTURE_DIR / "clean_pack.json")
    perturbed_pack = _read_json(FIXTURE_DIR / "perturbed_pack.json")
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")

    proposer = ClaudeProposer()
    proposal = proposer.propose(
        clean_pack,
        perturbed_pack,
        case_id=CASE_ID,
        strict_copy=os.getenv("CLAUDE_STRICT_COPY") == "1",
    )

    json_valid = isinstance(proposal, RevisionDelta)
    proposal_payload = proposal.model_dump(mode="json")
    print("CLAUDE_PROPOSER_OUTPUT=")
    print(json.dumps(proposal_payload, indent=2, sort_keys=True))

    verifier_accepted = False
    verifier_reasons: list[str] = []
    ledger_committed = False
    commit_outcome = "not_committed"

    if json_valid:
        _save_delta_if_requested(proposal)
        verifier_accepted, verifier_reasons = _verify_against_gold(
            proposal,
            gold_delta,
        )
        print(
            "CLAUDE_VERIFIER "
            f"status={'accepted' if verifier_accepted else 'rejected'} "
            f"reasons={json.dumps(verifier_reasons, sort_keys=True)}"
        )
        if verifier_accepted:
            run_dir = _commit_delta(tmp_path, proposal)
            ledger_committed = run_dir.is_dir()
            commit_outcome = str(run_dir)
    else:
        failure = proposal
        assert isinstance(failure, SealedFailureArtifact)
        verifier_reasons = [failure.error_type]
        print(
            "CLAUDE_VERIFIER "
            "status=rejected "
            f"reasons={json.dumps(verifier_reasons, sort_keys=True)}"
        )

    print(f"CLAUDE_COMMIT outcome={commit_outcome}")
    print(
        "CLAUDE_SUMMARY "
        f"json_valid={json_valid} "
        f"verifier_accepted={verifier_accepted} "
        f"ledger_committed={ledger_committed}"
    )
    assert json_valid, "Claude proposer did not return a valid RevisionDelta."


def test_claude_proposer_uses_structured_output_schema() -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    client = _FakeClaudeClient(gold_delta)
    proposer = ClaudeProposer(api_key="test-key", client=client)

    proposal = proposer.propose({}, {}, case_id=CASE_ID)

    assert isinstance(proposal, RevisionDelta)
    assert client.payload is not None
    assert client.payload["model"] == DEFAULT_CLAUDE_MODEL
    assert client.payload["messages"][0]["role"] == "user"
    assert client.payload["output_config"]["format"]["type"] == "json_schema"
    assert (
        client.payload["output_config"]["format"]["schema"]["properties"][
            "changed_states"
        ]["type"]
        == "array"
    )
    assert client.headers is not None
    assert client.headers["x-api-key"] == "test-key"
    assert client.headers["anthropic-version"] == "2023-06-01"


def test_claude_proposer_falls_back_to_tool_schema_if_json_output_rejected() -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    client = _FallbackClaudeClient(gold_delta)
    proposer = ClaudeProposer(api_key="test-key", client=client)

    proposal = proposer.propose({}, {}, case_id=CASE_ID)

    assert isinstance(proposal, RevisionDelta)
    assert len(client.payloads) == 2
    assert "output_config" in client.payloads[0]
    assert "output_config" not in client.payloads[1]
    assert client.payloads[1]["tools"][0]["name"] == CLAUDE_REVISION_DELTA_TOOL_NAME
    assert client.payloads[1]["tools"][0]["strict"] is True
    assert client.payloads[1]["tools"][0]["input_schema"] == REVISION_DELTA_JSON_SCHEMA
    assert client.payloads[1]["tool_choice"] == {
        "type": "tool",
        "name": CLAUDE_REVISION_DELTA_TOOL_NAME,
    }


def test_claude_prompt_includes_revision_precision_rules() -> None:
    proposer = ClaudeProposer(api_key="test-key")

    prompt = proposer._build_user_prompt(
        clean_pack={},
        perturbed_pack={},
        case_id=CASE_ID,
        strict_copy=False,
    )

    assert "background/admin branches as context" in prompt
    assert 'status "resolved"' in prompt
    assert "Compare scenario rank changes by scenario_id" in prompt


def test_claude_schema_encodes_supporting_evidence_map_as_json_string() -> None:
    supporting_evidence_map = REVISION_DELTA_JSON_SCHEMA["properties"][
        "supporting_evidence_map"
    ]

    assert supporting_evidence_map == {"type": "string"}


def test_claude_hydrates_before_after_json_strings_from_structured_output() -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    encoded_delta = _json_stringify_claude_schema_strings(gold_delta)
    client = _FakeClaudeClient(encoded_delta)
    proposer = ClaudeProposer(api_key="test-key", client=client)

    proposal = proposer.propose(
        _read_json(FIXTURE_DIR / "clean_pack.json"),
        _read_json(FIXTURE_DIR / "perturbed_pack.json"),
        case_id=CASE_ID,
    )

    assert isinstance(proposal, RevisionDelta)
    assert isinstance(proposal.changed_states[0].before, dict)
    assert isinstance(proposal.changed_states[0].after, dict)
    assert isinstance(proposal.supporting_evidence_map, dict)
    assert proposal.changed_states[0].before["state_id"] == "state:primary"
    assert proposal.changed_states[0].after["state_id"] == "state:primary"


def test_claude_schema_declares_additional_properties_for_all_objects() -> None:
    missing_paths = list(_object_schema_paths_missing_additional_properties())

    assert missing_paths == []
    assert _empty_schema_paths() == []
    assert REVISION_DELTA_JSON_SCHEMA["additionalProperties"] is False
    assert (
        REVISION_DELTA_JSON_SCHEMA["$defs"]["change"]["additionalProperties"]
        is False
    )
    assert (
        REVISION_DELTA_JSON_SCHEMA["$defs"]["scenario_rank_change"][
            "additionalProperties"
        ]
        is False
    )


def test_claude_missing_api_key_returns_sealed_failure() -> None:
    proposer = ClaudeProposer(api_key="")

    proposal = proposer.propose({}, {})

    assert isinstance(proposal, SealedFailureArtifact)
    assert proposal.provider == "claude"
    assert proposal.model == DEFAULT_CLAUDE_MODEL
    assert proposal.error_type == "missing_api_key"
    assert proposal.failure_id.startswith("sealed-failure:")


def test_extracts_claude_text_json_content() -> None:
    payload = {"schema_version": "1.0.0"}

    parsed = _extract_claude_json_content(
        {"content": [{"type": "text", "text": json.dumps(payload)}]}
    )

    assert parsed == payload


def test_extracts_claude_tool_use_json_content() -> None:
    payload = {"schema_version": "1.0.0"}

    parsed = _extract_claude_json_content(
        {
            "content": [
                {
                    "type": "tool_use",
                    "name": CLAUDE_REVISION_DELTA_TOOL_NAME,
                    "input": payload,
                }
            ]
        }
    )

    assert parsed == payload


def test_hydrate_revision_delta_json_fields_parses_null_and_objects() -> None:
    payload = {
        "changed_edges": [
            {
                "id": "edge:test",
                "change_type": "added",
                "before": "null",
                "after": "{\"edge_id\":\"edge:test\"}",
                "source_op_ids": [],
            }
        ],
        "changed_events": [],
        "changed_states": [],
        "new_unknowns": [],
        "resolved_unknowns": [],
        "supporting_evidence_map": "{\"edge:test\":[\"evidence:test\"]}",
    }

    hydrated = hydrate_revision_delta_json_fields(payload)

    assert hydrated["changed_edges"][0]["before"] is None
    assert hydrated["changed_edges"][0]["after"] == {"edge_id": "edge:test"}
    assert hydrated["supporting_evidence_map"] == {
        "edge:test": ["evidence:test"]
    }


def test_explicit_empty_claude_fallback_disables_default_fallback() -> None:
    proposer = ClaudeProposer(api_key="test", fallback_model="")

    assert proposer.fallback_model == ""


class _FakeClaudeClient:
    def __init__(self, delta_payload: dict[str, Any]) -> None:
        self.delta_payload = delta_payload
        self.payload: dict[str, Any] | None = None
        self.headers: dict[str, str] | None = None

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        self.headers = headers
        self.payload = json
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": json["model"],
                "content": [
                    {
                        "type": "text",
                        "text": dumps_canonical(self.delta_payload).decode("utf-8"),
                    }
                ],
                "stop_reason": "end_turn",
            },
            request=httpx.Request("POST", url),
        )


class _FallbackClaudeClient:
    def __init__(self, delta_payload: dict[str, Any]) -> None:
        self.delta_payload = delta_payload
        self.payloads: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> httpx.Response:
        self.payloads.append(json)
        request = httpx.Request("POST", url)
        if len(self.payloads) == 1:
            return httpx.Response(
                400,
                json={"error": {"message": "Unknown parameter: output_config"}},
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": json["model"],
                "content": [
                    {
                        "type": "tool_use",
                        "name": CLAUDE_REVISION_DELTA_TOOL_NAME,
                        "input": self.delta_payload,
                    }
                ],
                "stop_reason": "tool_use",
            },
            request=request,
        )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_stringify_claude_schema_strings(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.loads(json.dumps(payload))
    encoded["supporting_evidence_map"] = json.dumps(
        encoded.get("supporting_evidence_map", {}),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    for field_name in (
        "changed_edges",
        "changed_events",
        "changed_states",
        "new_unknowns",
        "resolved_unknowns",
    ):
        for item in encoded.get(field_name, []):
            if not isinstance(item, dict):
                continue
            for key in ("before", "after"):
                item[key] = json.dumps(
                    item.get(key),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
    return encoded


def _object_schema_paths_missing_additional_properties() -> list[str]:
    missing_paths: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if value.get("type") == "object" and "additionalProperties" not in value:
                missing_paths.append(path)
            for key, child in value.items():
                visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(REVISION_DELTA_JSON_SCHEMA, "$")
    return missing_paths


def _empty_schema_paths() -> list[str]:
    empty_paths: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if not value:
                empty_paths.append(path)
                return
            for key, child in value.items():
                visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(REVISION_DELTA_JSON_SCHEMA, "$")
    return empty_paths


def _verify_against_gold(
    proposal: RevisionDelta,
    gold_delta: dict[str, Any],
) -> tuple[bool, list[str]]:
    payload = proposal.model_dump(mode="json")
    reasons: list[str] = []

    required_changed_states = _ids(gold_delta["changed_states"])
    required_changed_edges = _ids(gold_delta["changed_edges"])
    required_resolved_unknowns = _ids(gold_delta["resolved_unknowns"])

    proposed_changed_states = _ids(payload["changed_states"])
    proposed_changed_edges = _ids(payload["changed_edges"])
    proposed_resolved_unknowns = _ids(payload["resolved_unknowns"])

    _append_missing(
        reasons,
        "missing_changed_states",
        required_changed_states - proposed_changed_states,
    )
    _append_missing(
        reasons,
        "missing_changed_edges",
        required_changed_edges - proposed_changed_edges,
    )
    _append_missing(
        reasons,
        "missing_resolved_unknowns",
        required_resolved_unknowns - proposed_resolved_unknowns,
    )

    forbidden_revisions = set(gold_delta["forbidden_revisions"])
    touched_ids = set().union(
        proposed_changed_states,
        proposed_changed_edges,
        _ids(payload["changed_events"]),
        _ids(payload["new_unknowns"]),
        proposed_resolved_unknowns,
    )
    collateral = forbidden_revisions & touched_ids
    _append_missing(reasons, "forbidden_revision_touched", collateral)

    required_preserved = set(gold_delta["preserved_items"])
    missing_preserved = required_preserved - set(payload["preserved_items"])
    _append_missing(reasons, "missing_preserved_items", missing_preserved)

    expected_artifact = gold_delta["named_evidence_artifact"]
    if payload["named_evidence_artifact"] != expected_artifact:
        reasons.append(
            "named_evidence_artifact_mismatch:"
            f"{payload['named_evidence_artifact']}!={expected_artifact}"
        )

    return not reasons, reasons


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {
        str(item["id"])
        for item in items
        if isinstance(item, dict) and "id" in item
    }


def _append_missing(reasons: list[str], label: str, values: set[str]) -> None:
    if values:
        reasons.append(f"{label}:{','.join(sorted(values))}")


def _commit_delta(tmp_path: Path, proposal: RevisionDelta) -> Path:
    evidence_bundle = _read_json(EVIDENCE_BUNDLE_PATH)
    output_obj = {
        "case_id": CASE_ID,
        "delta": proposal.model_dump(mode="json"),
        "verifier_status": "accepted",
    }
    sealed = finalize(
        evidence_bundle,
        output_obj,
        manifest_sha256="3" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.cuc_harness.claude.v1",
        created_utc="2026-05-25T00:00:00Z",
    )
    return write_run(ledger_root=str(tmp_path / "ledger"), **sealed)


def _save_delta_if_requested(proposal: RevisionDelta) -> None:
    output_path = os.getenv("CLAUDE_DELTA_OUTPUT_PATH")
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps_canonical(proposal.model_dump(mode="json")))
