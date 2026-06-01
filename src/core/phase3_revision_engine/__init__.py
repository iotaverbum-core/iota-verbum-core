"""Deterministic Phase 3 diagnostic self-healing helpers."""

from core.phase3_revision_engine.dependency_tracer import trace_dependency
from core.phase3_revision_engine.diagnostic_loop import diagnose_rejection
from core.phase3_revision_engine.failure_classifier import classify_failure
from core.phase3_revision_engine.repair_generator import generate_repair_instruction
from core.phase3_revision_engine.session_ledger import SessionLedger
from core.phase3_revision_engine.trust_chain import TrustChain, build_trust_chain
from core.phase3_revision_engine.types import (
    SEALED_DOCTRINE,
    DependencyTrace,
    DiagnosticLoopResult,
    DiagnosticLoopStatus,
    DoctrineContext,
    FailureFamily,
    FailureSymptom,
    ProtocolArtifact,
    ProtocolClause,
    RepairInstruction,
    SessionRecord,
)

__all__ = [
    "DependencyTrace",
    "DiagnosticLoopResult",
    "DiagnosticLoopStatus",
    "DoctrineContext",
    "FailureFamily",
    "FailureSymptom",
    "ProtocolArtifact",
    "ProtocolClause",
    "RepairInstruction",
    "SEALED_DOCTRINE",
    "SessionLedger",
    "SessionRecord",
    "TrustChain",
    "build_trust_chain",
    "classify_failure",
    "diagnose_rejection",
    "generate_repair_instruction",
    "trace_dependency",
]
