from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FailureFamily(str, Enum):
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    LAW_FAMILY_MISMATCH = "LAW_FAMILY_MISMATCH"
    GROUNDING_GAP = "GROUNDING_GAP"
    PRESERVATION_BREACH = "PRESERVATION_BREACH"


class DiagnosticLoopStatus(str, Enum):
    ACCEPTED = "accepted"
    REPAIRED = "repaired"
    HALT = "halt"


@dataclass(frozen=True)
class FailureSymptom:
    source_rejection_id: str
    code: str
    candidate_id: str
    candidate_kind: str
    path: str
    message: str
    attempt_index: int

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> FailureSymptom:
        return cls(
            source_rejection_id=str(
                payload.get("source_rejection_id")
                or payload.get("verdict_id")
                or payload.get("rejection_id")
                or payload.get("candidate_id")
                or ""
            ),
            code=str(payload.get("code", "")),
            candidate_id=str(payload.get("candidate_id", "")),
            candidate_kind=str(payload.get("candidate_kind", "")),
            path=str(payload.get("path", "")),
            message=str(payload.get("message", "")),
            attempt_index=int(payload.get("attempt_index", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_rejection_id": self.source_rejection_id,
            "code": self.code,
            "candidate_id": self.candidate_id,
            "candidate_kind": self.candidate_kind,
            "path": self.path,
            "message": self.message,
            "attempt_index": self.attempt_index,
        }


@dataclass(frozen=True)
class DependencyTrace:
    trace_id: str
    family: FailureFamily
    source_rejection_id: str
    target_operation_id: str
    target_claim_id: str | None
    grounding_evidence_ids: tuple[str, ...]
    preservation_constraints: tuple[str, ...]
    halt_reason: str | None
    checked_prior_claim_ids: tuple[str, ...]
    checked_trigger_claim_ids: tuple[str, ...]
    checked_evidence_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "family": self.family.value,
            "source_rejection_id": self.source_rejection_id,
            "target_operation_id": self.target_operation_id,
            "target_claim_id": self.target_claim_id,
            "grounding_evidence_ids": list(self.grounding_evidence_ids),
            "preservation_constraints": list(self.preservation_constraints),
            "halt_reason": self.halt_reason,
            "checked_prior_claim_ids": list(self.checked_prior_claim_ids),
            "checked_trigger_claim_ids": list(self.checked_trigger_claim_ids),
            "checked_evidence_ids": list(self.checked_evidence_ids),
        }


@dataclass(frozen=True)
class RepairInstruction:
    source_rejection_id: str
    target_operation_id: str
    required_fields: tuple[str, ...]
    grounding_evidence_ids: tuple[str, ...]
    preservation_constraints: tuple[str, ...]
    doctrine_family_id: str
    companion_law_ids: tuple[str, ...]
    candidate_kind: str = "repair_instruction"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_kind": self.candidate_kind,
            "source_rejection_id": self.source_rejection_id,
            "target_operation_id": self.target_operation_id,
            "required_fields": list(self.required_fields),
            "grounding_evidence_ids": list(self.grounding_evidence_ids),
            "preservation_constraints": list(self.preservation_constraints),
            "doctrine_family_id": self.doctrine_family_id,
            "companion_law_ids": list(self.companion_law_ids),
        }


@dataclass(frozen=True)
class DiagnosticLoopResult:
    result_id: str
    status: DiagnosticLoopStatus
    failure_symptom: FailureSymptom
    dependency_trace: DependencyTrace
    repair_instruction: RepairInstruction | None
    proposer_call_permitted: bool
    budget_consumed: bool
    ledger_advanced: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "status": self.status.value,
            "failure_symptom": self.failure_symptom.to_dict(),
            "dependency_trace": self.dependency_trace.to_dict(),
            "repair_instruction": (
                self.repair_instruction.to_dict()
                if self.repair_instruction is not None
                else None
            ),
            "proposer_call_permitted": self.proposer_call_permitted,
            "budget_consumed": self.budget_consumed,
            "ledger_advanced": self.ledger_advanced,
        }
