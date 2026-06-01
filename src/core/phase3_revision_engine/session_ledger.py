from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.phase3_revision_engine.types import (
    SEALED_DOCTRINE,
    DoctrineContext,
    SessionRecord,
)


def _session_hash(payload: dict[str, object]) -> str:
    return sha256_bytes(dumps_canonical(payload))


class SessionLedger:
    """Deterministic in-memory ledger for Phase 3 training-room sessions."""

    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}

    def open_session(
        self,
        model_id: str,
        model_version: str,
        generation_params: dict,
        case_id: str,
        doctrine_context: DoctrineContext = SEALED_DOCTRINE,
    ) -> str:
        doctrine_seal = doctrine_context.seal_hash()
        preimage = {
            "model_id": model_id,
            "model_version": model_version,
            "generation_params": generation_params,
            "case_id": case_id,
            "doctrine_version": doctrine_context.doctrine_version,
            "doctrine_digest": doctrine_context.doctrine_digest,
            "doctrine_seal": doctrine_seal,
        }
        session_id = "phase3-session:" + _session_hash(preimage)
        self._records[session_id] = SessionRecord(
            session_id=session_id,
            model_id=model_id,
            model_version=model_version,
            generation_params=dict(generation_params),
            case_id=case_id,
            doctrine_context=doctrine_context,
            doctrine_version=doctrine_context.doctrine_version,
            doctrine_digest=doctrine_context.doctrine_digest,
            doctrine_seal=doctrine_seal,
            opened_at=doctrine_context.sealed_at,
        )
        return session_id

    def get_session(self, session_id: str) -> SessionRecord:
        return self._records[session_id]


__all__ = ["SessionLedger"]
