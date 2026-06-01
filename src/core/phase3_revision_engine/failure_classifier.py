from __future__ import annotations

from core.phase3_revision_engine.types import FailureFamily, FailureSymptom

_CODES_BY_FAMILY: dict[FailureFamily, frozenset[str]] = {
    FailureFamily.SCHEMA_VIOLATION: frozenset(
        {
            "invalid_json",
            "invalid_structure",
            "conflicting_operations",
            "operation_conflict",
        }
    ),
    FailureFamily.PRESERVATION_BREACH: frozenset(
        {
            "forbidden_revision_touched",
            "missing_preserved_items",
        }
    ),
    FailureFamily.LAW_FAMILY_MISMATCH: frozenset(
        {
            "companion_law_violation",
            "law_family_mismatch",
        }
    ),
    FailureFamily.GROUNDING_GAP: frozenset(
        {
            "evidence_missing",
            "grounding_absent",
            "named_evidence_artifact_mismatch",
        }
    ),
}

_PRECEDENCE: tuple[FailureFamily, ...] = (
    FailureFamily.SCHEMA_VIOLATION,
    FailureFamily.PRESERVATION_BREACH,
    FailureFamily.LAW_FAMILY_MISMATCH,
    FailureFamily.GROUNDING_GAP,
)


class UnsupportedFailureCode(ValueError):
    """Raised when a verifier code is outside the sealed doctrine taxonomy."""


def classify_failure(symptom: FailureSymptom) -> FailureFamily:
    """Classify a failure symptom using deterministic doctrine precedence."""

    code = symptom.code.strip()
    for family in _PRECEDENCE:
        if code in _CODES_BY_FAMILY[family]:
            return family
    raise UnsupportedFailureCode(f"unsupported failure code: {symptom.code!r}")


__all__ = ["UnsupportedFailureCode", "classify_failure"]
