from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from core.phase3_revision_engine.types import SEALED_DOCTRINE, DoctrineContext


@dataclass(frozen=True)
class VerifierIssue:
    code: str
    operation_id: str
    doctrine_family: str
    message: str


@dataclass(frozen=True)
class VerifierResult:
    accepted: bool
    issues: tuple[VerifierIssue, ...]


class IotaVerifier:
    """Boundary-law verifier that reads every threshold from DoctrineContext."""

    def __init__(self, doctrine_context: DoctrineContext = SEALED_DOCTRINE) -> None:
        self.doctrine_context = doctrine_context

    def verify_operations(
        self,
        operations: Iterable[Mapping[str, Any]],
    ) -> VerifierResult:
        issues: list[VerifierIssue] = []
        non_preserve_seen: set[str] = set()
        for index, operation in enumerate(operations):
            operation_id = str(operation.get("id") or operation.get("operation_id"))
            if operation_id in {"", "None"}:
                operation_id = f"op:{index}"
            operation_type = str(operation.get("operation_type", ""))
            claim_id = str(operation.get("claim_id", ""))
            if operation_type not in self.doctrine_context.operation_types:
                issues.append(
                    VerifierIssue(
                        code="invalid_structure",
                        operation_id=operation_id,
                        doctrine_family="__SCHEMA__",
                        message="operation_type outside SEALED_DOCTRINE",
                    )
                )
                continue
            if operation_type != "Preserve" and claim_id:
                if claim_id in non_preserve_seen:
                    issues.append(
                        VerifierIssue(
                            code="operation_conflict",
                            operation_id=operation_id,
                            doctrine_family="__CONFLICT__",
                            message="multiple non-Preserve operations for claim_id",
                        )
                    )
                non_preserve_seen.add(claim_id)
            issues.extend(self._check_boundary_law(operation, operation_id))
        return VerifierResult(accepted=not issues, issues=tuple(issues))

    def _check_boundary_law(
        self,
        operation: Mapping[str, Any],
        operation_id: str,
    ) -> tuple[VerifierIssue, ...]:
        operation_type = str(operation.get("operation_type", ""))
        before = _optional_float(operation.get("before"))
        after = _optional_float(operation.get("after"))
        invalidates_support = bool(operation.get("invalidates_support", False))
        issues: list[VerifierIssue] = []
        if operation_type == "Retract" and before is not None:
            if before > self.doctrine_context.retract_threshold:
                issues.append(
                    VerifierIssue(
                        code="law_family_mismatch",
                        operation_id=operation_id,
                        doctrine_family="Residual_Support",
                        message="Retract is invalid while residual support remains",
                    )
                )
        if operation_type == "Weaken":
            if invalidates_support and (after or 0.0) <= (
                self.doctrine_context.collapse_residual_max
            ):
                issues.append(
                    VerifierIssue(
                        code="law_family_mismatch",
                        operation_id=operation_id,
                        doctrine_family="Support_Collapse_Without_Replacement",
                        message="Weaken is invalid after support collapse",
                    )
                )
            if before is not None and after is not None and after >= before:
                issues.append(
                    VerifierIssue(
                        code="law_family_mismatch",
                        operation_id=operation_id,
                        doctrine_family="Weaken_Direction",
                        message="Weaken requires after < before",
                    )
                )
        if operation_type == "Strengthen":
            if before is not None and after is not None and after <= before:
                issues.append(
                    VerifierIssue(
                        code="law_family_mismatch",
                        operation_id=operation_id,
                        doctrine_family="Strengthen_Direction",
                        message="Strengthen requires after > before",
                    )
                )
            if operation.get("contrary_evidence_count", 0):
                issues.append(
                    VerifierIssue(
                        code="law_family_mismatch",
                        operation_id=operation_id,
                        doctrine_family="Positive_Contrary_Fact",
                        message="Contrary evidence must be addressed",
                    )
                )
        if operation_type == "Preserve":
            if before is not None and after is not None and after != before:
                issues.append(
                    VerifierIssue(
                        code="law_family_mismatch",
                        operation_id=operation_id,
                        doctrine_family="Preserve_Invariant",
                        message="Preserve before and after must match",
                    )
                )
        return tuple(issues)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


__all__ = ["IotaVerifier", "VerifierIssue", "VerifierResult"]
