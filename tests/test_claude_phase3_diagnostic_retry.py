from __future__ import annotations

import json
from pathlib import Path

from scripts.claude_phase3_diagnostic_retry import (
    RetryDeltaResult,
    build_repair_instruction,
    build_retry_prompt,
    request_retry_delta,
)
from scripts.delta_gap_diagnostic import compare_deltas

from core.cuc_harness.claude_proposer import (
    REVISION_DELTA_JSON_SCHEMA,
    ClaudeProposer,
)
from core.cuc_harness.deepseek_proposer import RevisionDelta
from core.cuc_harness.verifier import verify_revision_delta

FIXTURE_DIR = Path(
    "benchmark/kaggle/fixtures/"
    "CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT"
)
CASE_ID = "CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT"


def test_claude_schema_allows_null_before_rank_for_new_scenarios() -> None:
    before_rank_schema = REVISION_DELTA_JSON_SCHEMA["$defs"][
        "scenario_rank_change"
    ]["properties"]["before_rank"]

    assert before_rank_schema["type"] == ["integer", "null"]


def test_build_repair_instruction_targets_hop3_grounding_gap() -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    rejected_delta = _build_rejected_hop3_delta(gold_delta)
    proposal = RevisionDelta.model_validate(rejected_delta)
    verification = verify_revision_delta(proposal, gold_delta)
    gap_report = compare_deltas(rejected_delta, gold_delta).to_dict()

    instruction = build_repair_instruction(
        case_id=CASE_ID,
        verification=verification,
        gap_report=gap_report,
        expected_delta=gold_delta,
    )

    assert instruction["candidate_kind"] == "repair_instruction"
    assert instruction["failure_family"] == "GROUNDING_GAP"
    assert instruction["target_operation_id"] == "op:hop3"
    required = instruction["required_fields"]
    assert required["source_op_ids_required"]["state:hop3_dependency"] == [
        "op:hop3"
    ]
    assert required["source_op_ids_required"]["event:hop3"] == ["op:hop3"]
    assert required["scenario_rank_changes"] == gold_delta["scenario_rank_changes"]
    assert required["supporting_evidence_map_required"]["event:response"] == [
        "evidence:response"
    ]
    assert "scenario:alternate" in required["remove_unexpected_items"]
    assert "supporting_evidence_map.scenario:alternate" in (
        required["remove_unexpected_items"]
    )
    assert instruction["grounding_evidence_ids"] == [
        "evidence:hop3",
        "evidence:response",
    ]
    assert instruction["preservation_constraints"] == [
        "state:secondary",
        "edge:secondary_support",
        "unknown:secondary",
    ]


def test_retry_prompt_appends_verifier_feedback_and_repair_instruction() -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    rejected_delta = _build_rejected_hop3_delta(gold_delta)
    proposal = RevisionDelta.model_validate(rejected_delta)
    verification = verify_revision_delta(proposal, gold_delta)
    gap_report = compare_deltas(rejected_delta, gold_delta).to_dict()
    instruction = build_repair_instruction(
        case_id=CASE_ID,
        verification=verification,
        gap_report=gap_report,
        expected_delta=gold_delta,
    )

    prompt = build_retry_prompt(
        proposer=ClaudeProposer(api_key="test-key"),
        clean_pack=_read_json(FIXTURE_DIR / "clean_pack.json"),
        perturbed_pack=_read_json(FIXTURE_DIR / "perturbed_pack.json"),
        case_id=CASE_ID,
        strict_copy=False,
        baseline_delta=rejected_delta,
        baseline_verification=verification,
        baseline_gap=gap_report,
        repair_instruction=instruction,
    )

    assert "DIAGNOSTIC_REPAIR_INSTRUCTION:" in prompt
    assert "VERIFIER_FEEDBACK:" in prompt
    assert '"target_operation_id": "op:hop3"' in prompt
    assert '"before_rank": null' in prompt
    assert "Preserve every ID in preservation_constraints." in prompt


def test_request_retry_delta_preserves_successful_fallback_model(
    monkeypatch,
) -> None:
    proposer = ClaudeProposer(
        api_key="test-key",
        model="claude-primary",
        fallback_model="claude-fallback",
    )
    expected_delta = RevisionDelta.model_validate(
        _read_json(FIXTURE_DIR / "expected_delta.json")
    )
    requested_models: list[str] = []

    def fake_request_delta(*, model: str, user_prompt: str):
        requested_models.append(model)
        assert user_prompt == "retry prompt"
        if model == "claude-primary":
            return proposer._failure(  # noqa: SLF001
                model=model,
                error_type="rate_limit",
                message="primary unavailable",
            )
        return expected_delta

    monkeypatch.setattr(proposer, "_request_delta", fake_request_delta)

    result = request_retry_delta(proposer, "retry prompt")

    assert isinstance(result, RetryDeltaResult)
    assert result.delta == expected_delta
    assert result.model == "claude-fallback"
    assert requested_models == ["claude-primary", "claude-fallback"]


def _build_rejected_hop3_delta(gold_delta: dict) -> dict:
    rejected = json.loads(json.dumps(gold_delta))
    source_op_targets = {
        "state:hop3_dependency",
        "edge:hop3_dependency",
        "event:hop3",
        "unknown:hop3_dependency",
    }
    for field_name in (
        "changed_edges",
        "changed_events",
        "changed_states",
        "new_unknowns",
    ):
        for item in rejected[field_name]:
            if item["id"] in source_op_targets:
                item["source_op_ids"] = []
    rejected["scenario_rank_changes"].append(
        {
            "scenario_id": "scenario:alternate",
            "before_rank": 2,
            "after_rank": 2,
        }
    )
    rejected["supporting_evidence_map"].pop("event:response")
    rejected["supporting_evidence_map"].pop("event:hop3")
    rejected["supporting_evidence_map"]["scenario:alternate"] = [
        "evidence:secondary",
        "evidence:response",
    ]
    rejected["new_unknowns"][0]["before"] = None
    return rejected


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
