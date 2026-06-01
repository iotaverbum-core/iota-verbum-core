from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.phase3_revision_engine.types import (
    DependencyTrace,
    FailureFamily,
    FailureSymptom,
    RepairInstruction,
)

_DOCTRINE_FAMILY_IDS = {
    FailureFamily.SCHEMA_VIOLATION: "phase3.diagnostic.family.schema_violation.v1",
    FailureFamily.LAW_FAMILY_MISMATCH: (
        "phase3.diagnostic.family.law_family_mismatch.v1"
    ),
    FailureFamily.GROUNDING_GAP: "phase3.diagnostic.family.grounding_gap.v1",
    FailureFamily.PRESERVATION_BREACH: (
        "phase3.diagnostic.family.preservation_breach.v1"
    ),
}

_REPAIR_SCOPE_MINIMALITY = "phase3.diagnostic.law.repair_scope_minimality.v1"
_HALT_ON_UNGROUNDABLE = "phase3.diagnostic.law.halt_on_ungroundable_repair.v1"

_LAW_BY_OPERATION_KIND = {
    "NewClaim": "phase3.law.narrower_novel_essence.v1",
    "Preserve": "phase3.law.preservation_ack.v1",
    "Retract": "phase3.law.completed_incompatible_outcome.v1",
    "Revise": "phase3.law.revision_by_new_support.v1",
    "Weaken": "phase3.law.revision_by_new_support.v1",
}


def _sorted_tuple(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if value}))


def _schema_field_type_hint(symptom: FailureSymptom) -> str:
    if symptom.code in {"operation_conflict", "conflicting_operations"}:
        return "remove_or_merge_conflict"
    path_tail = symptom.path.rsplit("/", 1)[-1]
    message = symptom.message.lower()
    if "array" in message or path_tail.endswith("_ids"):
        return "array<string>"
    if "enum" in message or "one of" in message:
        return "enum"
    if "id" in path_tail:
        return "string"
    return "required"


def _law_required_fields(
    symptom: FailureSymptom,
    operation: Mapping[str, Any],
) -> tuple[str, ...]:
    message = symptom.message.lower()
    if "without a retract" in message:
        return (
            "/claimed_companion_law_ids:remove:"
            "phase3.law.retraction_companion_newclaim.v1",
        )
    if "companion" in message and "required" in message:
        return (
            "/claimed_companion_law_ids:"
            "phase3.law.retraction_companion_newclaim.v1",
        )

    operation_kind = str(operation.get("operation_kind", ""))
    law_id = _LAW_BY_OPERATION_KIND.get(operation_kind)
    if law_id is None:
        return (f"{symptom.path}:allowed_law_family",)
    return (f"{symptom.path}:{law_id}",)


def _grounding_required_fields(symptom: FailureSymptom) -> tuple[str, ...]:
    fields = [symptom.path or "/operations/*/grounding_evidence_ids"]
    if "basis_trigger_claim_ids" in symptom.path:
        fields.append("/operations/*/grounding_evidence_ids")
    return _sorted_tuple(fields)


def _preservation_required_fields(symptom: FailureSymptom) -> tuple[str, ...]:
    fields = ["/preserved_items"]
    if symptom.code == "forbidden_revision_touched":
        operation_path = (
            symptom.path.rsplit("/", 1)[0] if symptom.path else "/operations/*"
        )
        fields.insert(0, f"{operation_path}:remove_or_replace")
    return _sorted_tuple(fields)


def generate_repair_instruction(
    *,
    symptom: FailureSymptom,
    trace: DependencyTrace,
    operation: Mapping[str, Any],
    guidance: str = "",
) -> RepairInstruction | None:
    if trace.halt_reason is not None:
        return None

    if trace.family is FailureFamily.SCHEMA_VIOLATION:
        required_fields = (f"{symptom.path}:{_schema_field_type_hint(symptom)}",)
        grounding_evidence_ids: tuple[str, ...] = ()
        companion_law_ids = (_REPAIR_SCOPE_MINIMALITY,)
    elif trace.family is FailureFamily.LAW_FAMILY_MISMATCH:
        required_fields = _law_required_fields(symptom, operation)
        grounding_evidence_ids = ()
        companion_law_ids = (_REPAIR_SCOPE_MINIMALITY,)
    elif trace.family is FailureFamily.GROUNDING_GAP:
        required_fields = _grounding_required_fields(symptom)
        grounding_evidence_ids = trace.grounding_evidence_ids
        companion_law_ids = (_HALT_ON_UNGROUNDABLE, _REPAIR_SCOPE_MINIMALITY)
    else:
        required_fields = _preservation_required_fields(symptom)
        grounding_evidence_ids = ()
        companion_law_ids = (_REPAIR_SCOPE_MINIMALITY,)

    return RepairInstruction(
        source_rejection_id=symptom.source_rejection_id,
        target_operation_id=trace.target_operation_id,
        required_fields=_sorted_tuple(list(required_fields)),
        grounding_evidence_ids=grounding_evidence_ids,
        preservation_constraints=trace.preservation_constraints,
        doctrine_family_id=_DOCTRINE_FAMILY_IDS[trace.family],
        companion_law_ids=tuple(sorted(companion_law_ids)),
        guidance=guidance,
    )


__all__ = ["generate_repair_instruction"]
