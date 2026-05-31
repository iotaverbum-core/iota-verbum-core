"""Deterministic Phase 3 diagnostic self-healing helpers."""

from core.phase3_revision_engine.dependency_tracer import trace_dependency
from core.phase3_revision_engine.diagnostic_loop import diagnose_rejection
from core.phase3_revision_engine.failure_classifier import classify_failure
from core.phase3_revision_engine.repair_generator import generate_repair_instruction
from core.phase3_revision_engine.types import (
    DependencyTrace,
    DiagnosticLoopResult,
    DiagnosticLoopStatus,
    FailureFamily,
    FailureSymptom,
    RepairInstruction,
)

__all__ = [
    "DependencyTrace",
    "DiagnosticLoopResult",
    "DiagnosticLoopStatus",
    "FailureFamily",
    "FailureSymptom",
    "RepairInstruction",
    "classify_failure",
    "diagnose_rejection",
    "generate_repair_instruction",
    "trace_dependency",
]
