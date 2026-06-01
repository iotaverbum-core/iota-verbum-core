from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet


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
class DoctrineContext:
    """
    The sealed doctrine substrate. Carry through the full call stack.
    Never instantiate ad-hoc; use SEALED_DOCTRINE below.
    All boundary law thresholds are read from this object.
    """

    doctrine_version: str
    doctrine_digest: str
    operation_types: FrozenSet[str]
    doctrine_families: FrozenSet[str]
    retract_threshold: float
    max_non_preserve_ops_per_claim: int
    collapse_residual_max: float
    sealed_at: str

    def seal_hash(self) -> str:
        """Return the SHA-256 of the canonical doctrine context JSON."""

        payload = {
            "doctrine_version": self.doctrine_version,
            "doctrine_digest": self.doctrine_digest,
            "operation_types": sorted(self.operation_types),
            "doctrine_families": sorted(self.doctrine_families),
            "retract_threshold": self.retract_threshold,
            "max_non_preserve_ops_per_claim": self.max_non_preserve_ops_per_claim,
            "collapse_residual_max": self.collapse_residual_max,
            "sealed_at": self.sealed_at,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


SEALED_DOCTRINE = DoctrineContext(
    doctrine_version="phase3.diagnostic_self_healing.doctrine.v1",
    doctrine_digest="matrix:a6d67df8",
    operation_types=frozenset(
        {
            "Preserve",
            "Weaken",
            "Retract",
            "Strengthen",
            "NewlyUnknown",
            "NewClaim",
        }
    ),
    doctrine_families=frozenset(
        {
            "Residual_Support",
            "Support_Collapse_Without_Replacement",
            "Positive_Contrary_Fact",
            "Weaken_Direction",
            "Strengthen_Direction",
            "Preserve_Invariant",
            "Orthogonal_Trigger",
        }
    ),
    retract_threshold=0.30,
    max_non_preserve_ops_per_claim=1,
    collapse_residual_max=0.05,
    sealed_at="2026-05-01T00:00:00Z",
)


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
    guidance: str = ""
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
            "guidance": self.guidance,
        }


@dataclass
class ProtocolClause:
    """A constraint clause derived from a doctrine family repair pattern."""

    doctrine_family: str
    failure_family: str
    frequency: int
    prompt_clause: str


@dataclass
class ProtocolArtifact:
    """
    Model-specific prompt scaffold synthesised from a session repair history.

    An empty clauses list is valid; it means the model converged on attempt 1.
    """

    model_id: str
    session_id: str
    clauses: list[ProtocolClause]
    system_prompt: str


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    model_id: str
    model_version: str
    generation_params: dict[str, Any]
    case_id: str
    doctrine_context: DoctrineContext
    doctrine_version: str
    doctrine_digest: str
    doctrine_seal: str
    opened_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "generation_params": dict(self.generation_params),
            "case_id": self.case_id,
            "doctrine_context": {
                "doctrine_version": self.doctrine_context.doctrine_version,
                "doctrine_digest": self.doctrine_context.doctrine_digest,
                "operation_types": sorted(self.doctrine_context.operation_types),
                "doctrine_families": sorted(self.doctrine_context.doctrine_families),
                "retract_threshold": self.doctrine_context.retract_threshold,
                "max_non_preserve_ops_per_claim": (
                    self.doctrine_context.max_non_preserve_ops_per_claim
                ),
                "collapse_residual_max": self.doctrine_context.collapse_residual_max,
                "sealed_at": self.doctrine_context.sealed_at,
            },
            "doctrine_version": self.doctrine_version,
            "doctrine_digest": self.doctrine_digest,
            "doctrine_seal": self.doctrine_seal,
            "opened_at": self.opened_at,
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
