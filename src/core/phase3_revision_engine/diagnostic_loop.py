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
    SEALED_DOCTRINE,
    DependencyTrace,
    DiagnosticLoopResult,
    DiagnosticLoopStatus,
    FailureFamily,
    FailureSymptom,
)

REPAIR_GUIDANCE: dict[str, str] = {
    "Residual_Support": (
        "Residual support remains (support_level > {retract_threshold}, "
        "invalidates_support=False). Use Weaken not Retract. "
        "Set 'before' to the EXACT support_level from the prior graph claim. "
        "Set 'after' to a strictly smaller value (after < before)."
    ),
    "Support_Collapse_Without_Replacement": (
        "invalidates_support=True means all evidential support has been eliminated. "
        "Use Retract, not Weaken. Weaken is only valid when residual support "
        "remains above {collapse_residual_max}. If this claim has a natural "
        "successor, pair Retract with a NewClaim operation for the replacement "
        "assertion."
    ),
    "Weaken_Direction": (
        "Weaken requires after < before (strict inequality — equal values are "
        "invalid). Set 'before' to the EXACT support_level from the prior graph "
        "claim — do not estimate or approximate. Set 'after' to a value strictly "
        "less than that number."
    ),
    "Strengthen_Direction": (
        "Strengthen requires after > before (strict inequality). "
        "Set 'before' to the EXACT support_level from the prior graph claim. "
        "Set 'after' to a value strictly greater than that number."
    ),
    "Positive_Contrary_Fact": (
        "The trigger contains contrary evidence that must be addressed before "
        "Strengthen is valid. Add contrary_evidence_addressed: true and a "
        "'rationale' field explaining why the strengthening survives the contrary "
        "evidence. If the contrary evidence is decisive, use Weaken instead."
    ),
    "Preserve_Invariant": (
        "Preserve confirms a claim is unchanged by the trigger. "
        "The 'before' and 'after' fields, if both present, must be identical. "
        "Simplest correct form: omit 'after' entirely."
    ),
    "Orthogonal_Trigger": (
        "The trigger is orthogonal to this claim — it does not provide evidence "
        "for or against it. Use Preserve. Do not apply Weaken, Strengthen, or "
        "any other operation to claims the trigger does not reach."
    ),
    "__SCHEMA__": (
        "Schema violation. Ensure every operation has: "
        "(1) 'id' — unique string; "
        "(2) 'operation_type' — one of: Preserve, Weaken, Retract, Strengthen, "
        "NewlyUnknown, NewClaim; "
        "(3) 'claim_id' for all types except NewClaim; "
        "(4) 'claim_content' for NewClaim (no claim_id). "
        "No other operation_type values are valid."
    ),
    "__CONFLICT__": (
        "Operation conflict: only one non-Preserve operation is permitted per "
        "claim_id within a single delta. Remove or merge the conflicting "
        "operations. Preserve operations do not conflict with each other."
    ),
    "__FALLBACK__": (
        "Unknown doctrine family. Review all operations against the six lawful "
        "operation types and the sealed boundary law constraints. "
        "Doctrine: {doctrine_version}."
    ),
}


def _hash_obj(payload: dict[str, Any]) -> str:
    return sha256_bytes(dumps_canonical(payload))


def _guidance_key(
    *,
    symptom: FailureSymptom,
    trace: DependencyTrace,
    operation: Mapping[str, Any],
) -> str:
    if symptom.code in {"operation_conflict", "conflicting_operations"}:
        return "__CONFLICT__"
    if trace.family is FailureFamily.SCHEMA_VIOLATION:
        return "__SCHEMA__"

    candidates = [
        operation.get("doctrine_family"),
        operation.get("doctrine_family_id"),
        operation.get("claimed_doctrine_family"),
        operation.get("claimed_law_family_id"),
        symptom.message,
        symptom.path,
    ]
    joined = " ".join(str(candidate) for candidate in candidates if candidate)
    for doctrine_family in sorted(SEALED_DOCTRINE.doctrine_families):
        if doctrine_family in joined:
            return doctrine_family
    return "__FALLBACK__"


def format_repair_guidance(
    *,
    symptom: FailureSymptom,
    trace: DependencyTrace,
    operation: Mapping[str, Any],
) -> str:
    doctrine_family = _guidance_key(
        symptom=symptom,
        trace=trace,
        operation=operation,
    )
    raw_guidance = REPAIR_GUIDANCE.get(
        doctrine_family,
        REPAIR_GUIDANCE["__FALLBACK__"],
    )
    return raw_guidance.format(
        retract_threshold=SEALED_DOCTRINE.retract_threshold,
        collapse_residual_max=SEALED_DOCTRINE.collapse_residual_max,
        doctrine_version=SEALED_DOCTRINE.doctrine_version,
    )


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
    guidance = format_repair_guidance(
        symptom=symptom,
        trace=trace,
        operation=operation,
    )
    repair_instruction = generate_repair_instruction(
        symptom=symptom,
        trace=trace,
        operation=operation,
        guidance=guidance,
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


__all__ = ["REPAIR_GUIDANCE", "diagnose_rejection", "format_repair_guidance"]
