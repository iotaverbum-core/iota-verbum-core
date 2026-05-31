from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.phase3_revision_engine.dependency_tracer import trace_dependency
from core.phase3_revision_engine.failure_classifier import (
    UnsupportedFailureCode,
    classify_failure,
)
from core.phase3_revision_engine.repair_generator import generate_repair_instruction
from core.phase3_revision_engine.types import (
    DependencyTrace,
    DiagnosticLoopResult,
    DiagnosticLoopStatus,
    FailureFamily,
    FailureSymptom,
)


def _hash_obj(payload: dict[str, Any]) -> str:
    return sha256_bytes(dumps_canonical(payload))


def _halt_trace(
    *,
    symptom: FailureSymptom,
    operation: Mapping[str, Any],
    family: FailureFamily = FailureFamily.SCHEMA_VIOLATION,
    halt_reason: str,
) -> DependencyTrace:
    target_operation_id = str(
        operation.get("target_operation_id")
        or operation.get("operation_id")
        or symptom.candidate_id
    )
    preimage = {
        "family": family.value,
        "source_rejection_id": symptom.source_rejection_id,
        "target_operation_id": target_operation_id,
        "halt_reason": halt_reason,
    }
    return DependencyTrace(
        trace_id="phase3-diagnostic-trace:" + _hash_obj(preimage),
        family=family,
        source_rejection_id=symptom.source_rejection_id,
        target_operation_id=target_operation_id,
        target_claim_id=None,
        grounding_evidence_ids=(),
        preservation_constraints=(),
        halt_reason=halt_reason,
        checked_prior_claim_ids=(),
        checked_trigger_claim_ids=(),
        checked_evidence_ids=(),
    )


def _result(
    *,
    status: DiagnosticLoopStatus,
    symptom: FailureSymptom,
    trace: DependencyTrace,
    repair_instruction: Any,
    proposer_call_permitted: bool,
    budget_consumed: bool,
) -> DiagnosticLoopResult:
    preimage = {
        "status": status.value,
        "failure_symptom": symptom.to_dict(),
        "dependency_trace": trace.to_dict(),
        "repair_instruction": (
            repair_instruction.to_dict()
            if repair_instruction is not None
            else None
        ),
        "proposer_call_permitted": proposer_call_permitted,
        "budget_consumed": budget_consumed,
        "ledger_advanced": False,
    }
    return DiagnosticLoopResult(
        result_id="phase3-diagnostic-result:" + _hash_obj(preimage),
        status=status,
        failure_symptom=symptom,
        dependency_trace=trace,
        repair_instruction=repair_instruction,
        proposer_call_permitted=proposer_call_permitted,
        budget_consumed=budget_consumed,
        ledger_advanced=False,
    )


def diagnose_rejection(
    *,
    rejection: Mapping[str, Any] | FailureSymptom,
    prior_graph: Mapping[str, Any],
    trigger_graph: Mapping[str, Any],
    operation: Mapping[str, Any],
    verifier_context: Mapping[str, Any] | None = None,
    proposer_retry_budget_remaining: int = 1,
) -> DiagnosticLoopResult:
    symptom = (
        rejection
        if isinstance(rejection, FailureSymptom)
        else FailureSymptom.from_mapping(dict(rejection))
    )
    if proposer_retry_budget_remaining <= 0:
        trace = _halt_trace(
            symptom=symptom,
            operation=operation,
            halt_reason="budget_exhausted",
        )
        return _result(
            status=DiagnosticLoopStatus.HALT,
            symptom=symptom,
            trace=trace,
            repair_instruction=None,
            proposer_call_permitted=False,
            budget_consumed=False,
        )

    try:
        family = classify_failure(symptom)
    except UnsupportedFailureCode:
        trace = _halt_trace(
            symptom=symptom,
            operation=operation,
            halt_reason="unsupported_failure_code",
        )
        return _result(
            status=DiagnosticLoopStatus.HALT,
            symptom=symptom,
            trace=trace,
            repair_instruction=None,
            proposer_call_permitted=False,
            budget_consumed=False,
        )

    trace = trace_dependency(
        family=family,
        symptom=symptom,
        prior_graph=prior_graph,
        trigger_graph=trigger_graph,
        operation=operation,
        verifier_context=verifier_context,
    )
    repair_instruction = generate_repair_instruction(
        symptom=symptom,
        trace=trace,
        operation=operation,
    )
    if repair_instruction is None:
        return _result(
            status=DiagnosticLoopStatus.HALT,
            symptom=symptom,
            trace=trace,
            repair_instruction=None,
            proposer_call_permitted=False,
            budget_consumed=False,
        )

    return _result(
        status=DiagnosticLoopStatus.REPAIRED,
        symptom=symptom,
        trace=trace,
        repair_instruction=repair_instruction,
        proposer_call_permitted=True,
        budget_consumed=False,
    )


__all__ = ["diagnose_rejection"]
