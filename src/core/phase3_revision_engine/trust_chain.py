from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.phase3_revision_engine.types import DoctrineContext, SessionRecord


@dataclass(frozen=True)
class TrustChain:
    session_id: str
    model_id: str
    case_id: str
    doctrine_context: DoctrineContext
    doctrine_seal: str
    artifacts: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    chain_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "model_id": self.model_id,
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
            "doctrine_seal": self.doctrine_seal,
            "artifacts": [dict(artifact) for artifact in self.artifacts],
            "chain_hash": self.chain_hash,
        }


def build_trust_chain(
    *,
    session_record: SessionRecord,
    artifacts: tuple[dict[str, Any], ...] = (),
) -> TrustChain:
    doctrine_context = session_record.doctrine_context
    doctrine_seal = doctrine_context.seal_hash()
    assert doctrine_seal == session_record.doctrine_seal
    preimage = {
        "session_id": session_record.session_id,
        "model_id": session_record.model_id,
        "case_id": session_record.case_id,
        "doctrine_seal": doctrine_seal,
        "artifacts": list(artifacts),
    }
    chain_hash = "phase3-trust-chain:" + sha256_bytes(dumps_canonical(preimage))
    return TrustChain(
        session_id=session_record.session_id,
        model_id=session_record.model_id,
        case_id=session_record.case_id,
        doctrine_context=doctrine_context,
        doctrine_seal=doctrine_seal,
        artifacts=artifacts,
        chain_hash=chain_hash,
    )


__all__ = ["TrustChain", "build_trust_chain"]
