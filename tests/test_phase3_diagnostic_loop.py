from __future__ import annotations

from core.cuc_harness.phase5_orchestration import append_repair_instruction_feedback
from core.phase3_revision_engine import diagnose_rejection
from core.phase3_revision_engine.types import DiagnosticLoopStatus, FailureFamily


def _prior_graph(*, preserved: list[str] | None = None) -> dict[str, object]:
    preserved_ids = preserved or ["claim:sibling-stable"]
    return {
        "prior_claim_ids": ["claim:target-prior", *preserved_ids],
        "preserved_claim_ids": preserved_ids,
    }


def _trigger_graph(
    *,
    target_claim_id: str = "claim:target-trigger",
    evidence_ids: list[str] | None = None,
) -> dict[str, object]:
    evidence = evidence_ids if evidence_ids is not None else ["evidence:trigger"]
    return {
        "trigger_claim_ids": [target_claim_id],
        "evidence_ids": evidence,
        "support_edges": [
            [evidence_id, target_claim_id, "grounds"] for evidence_id in evidence
        ],
    }


def _rejection(code: str, path: str = "/operations/0") -> dict[str, object]:
    return {
        "source_rejection_id": "rejection:test",
        "code": code,
        "candidate_id": "candidate:test",
        "candidate_kind": "revision_delta",
        "path": path,
        "message": f"mock verifier rejection for {code}",
        "attempt_index": 1,
    }


def _operation(
    *,
    operation_kind: str = "Revise",
    target_claim_id: str = "claim:target-prior",
) -> dict[str, str]:
    return {
        "target_operation_id": "op:test",
        "operation_kind": operation_kind,
        "target_claim_id": target_claim_id,
        "claimed_law_family_id": "phase3.law.revision_by_new_support.v1",
    }


def test_happy_path_emits_grounded_repair_instruction() -> None:
    result = diagnose_rejection(
        rejection=_rejection(
            "grounding_absent",
            "/operations/0/grounding_evidence_ids",
        ),
        prior_graph=_prior_graph(),
        trigger_graph=_trigger_graph(),
        operation=_operation(),
    )

    assert result.status is DiagnosticLoopStatus.REPAIRED
    assert result.dependency_trace.family is FailureFamily.GROUNDING_GAP
    assert result.repair_instruction is not None
    assert result.repair_instruction.grounding_evidence_ids == ("evidence:trigger",)
    assert result.repair_instruction.candidate_kind == "repair_instruction"
    assert result.proposer_call_permitted is True
    assert result.budget_consumed is False
    assert result.ledger_advanced is False

    feedback = append_repair_instruction_feedback([], result)
    assert feedback == [result.repair_instruction.to_dict()]


def test_correct_symptom_recovers_from_wrong_family_temptation() -> None:
    result = diagnose_rejection(
        rejection={
            **_rejection("invalid_structure", "/operations/0/grounding_evidence_ids"),
            "message": (
                "grounding evidence is mentioned, but the array field is invalid"
            ),
        },
        prior_graph=_prior_graph(),
        trigger_graph=_trigger_graph(),
        operation=_operation(),
    )

    assert result.status is DiagnosticLoopStatus.REPAIRED
    assert result.dependency_trace.family is FailureFamily.SCHEMA_VIOLATION
    assert result.repair_instruction is not None
    assert result.repair_instruction.grounding_evidence_ids == ()
    assert result.repair_instruction.required_fields == (
        "/operations/0/grounding_evidence_ids:array<string>",
    )


def test_halts_on_ungroundable_grounding_gap() -> None:
    result = diagnose_rejection(
        rejection=_rejection(
            "grounding_absent",
            "/operations/0/grounding_evidence_ids",
        ),
        prior_graph=_prior_graph(),
        trigger_graph=_trigger_graph(evidence_ids=[]),
        operation=_operation(),
    )

    assert result.status is DiagnosticLoopStatus.HALT
    assert result.dependency_trace.halt_reason == "ungroundable_repair"
    assert result.repair_instruction is None
    assert result.proposer_call_permitted is False
    assert result.ledger_advanced is False


def test_preservation_constraint_enforced_in_repair_instruction() -> None:
    result = diagnose_rejection(
        rejection=_rejection(
            "forbidden_revision_touched",
            "/operations/1/target_claim_id",
        ),
        prior_graph=_prior_graph(preserved=["claim:stable-notice"]),
        trigger_graph=_trigger_graph(),
        operation=_operation(target_claim_id="claim:stable-notice"),
    )

    assert result.status is DiagnosticLoopStatus.REPAIRED
    assert result.dependency_trace.family is FailureFamily.PRESERVATION_BREACH
    assert result.repair_instruction is not None
    assert result.repair_instruction.preservation_constraints == (
        "claim:stable-notice",
    )
    assert "/operations/1:remove_or_replace" in (
        result.repair_instruction.required_fields
    )


def test_budget_exhaustion_halts_without_proposer_or_ledger_advance() -> None:
    result = diagnose_rejection(
        rejection=_rejection(
            "grounding_absent",
            "/operations/0/grounding_evidence_ids",
        ),
        prior_graph=_prior_graph(),
        trigger_graph=_trigger_graph(),
        operation=_operation(),
        proposer_retry_budget_remaining=0,
    )

    assert result.status is DiagnosticLoopStatus.HALT
    assert result.dependency_trace.halt_reason == "budget_exhausted"
    assert result.repair_instruction is None
    assert result.proposer_call_permitted is False
    assert result.budget_consumed is False
    assert result.ledger_advanced is False
