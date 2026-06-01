from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from core.phase3_revision_engine.types import (
    ProtocolArtifact,
    ProtocolClause,
    RepairInstruction,
    SessionRecord,
)


def synthesise_protocol(
    *,
    session_record: SessionRecord,
    repair_history: Iterable[RepairInstruction],
) -> ProtocolArtifact:
    repairs = list(repair_history)
    counts = Counter(
        (
            repair.doctrine_family_id,
            repair.to_dict().get("failure_family", "diagnostic_repair"),
            repair.guidance,
        )
        for repair in repairs
    )
    clauses = [
        ProtocolClause(
            doctrine_family=doctrine_family,
            failure_family=failure_family,
            frequency=frequency,
            prompt_clause=f"CONSTRAINT: {guidance}",
        )
        for (doctrine_family, failure_family, guidance), frequency in counts.items()
    ]
    clauses.sort(key=lambda clause: (-clause.frequency, clause.doctrine_family))
    prompt_lines = [
        "You are the proposer inside an Iota Verbum verifier-governed loop.",
        "The verifier is external and authoritative.",
    ]
    prompt_lines.extend(clause.prompt_clause for clause in clauses)
    return ProtocolArtifact(
        model_id=session_record.model_id,
        session_id=session_record.session_id,
        clauses=clauses,
        system_prompt="\n".join(prompt_lines),
    )


__all__ = ["synthesise_protocol"]
