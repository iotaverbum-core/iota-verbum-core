from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.phase3_revision_engine.types import DiagnosticLoopResult


def append_repair_instruction_feedback(
    accumulated_feedback: Sequence[Mapping[str, Any]],
    diagnostic_result: DiagnosticLoopResult,
) -> list[dict[str, Any]]:
    """Append a repair instruction as Phase 5 retry feedback without mutation."""

    feedback = [dict(item) for item in accumulated_feedback]
    if diagnostic_result.repair_instruction is None:
        return feedback
    feedback.append(diagnostic_result.repair_instruction.to_dict())
    return feedback


__all__ = ["append_repair_instruction_feedback"]
