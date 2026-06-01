from __future__ import annotations

from dataclasses import dataclass

from core.phase3_revision_engine.trust_chain import TrustChain
from core.phase3_revision_engine.types import ProtocolArtifact, SessionRecord


@dataclass(frozen=True)
class ProductionLoopResult:
    session_record: SessionRecord
    baseline_score: float
    trained_score: float
    passed_as_candidate_proposer: bool
    protocol_artifact: ProtocolArtifact | None
    trust_chain: TrustChain


__all__ = ["ProductionLoopResult"]
