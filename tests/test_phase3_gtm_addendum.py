from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from core.phase3_revision_engine.diagnostic_loop import (
    REPAIR_GUIDANCE,
    diagnose_rejection,
)
from core.phase3_revision_engine.session_ledger import SessionLedger
from core.phase3_revision_engine.trust_chain import TrustChain, build_trust_chain
from core.phase3_revision_engine.types import (
    SEALED_DOCTRINE,
    DoctrineContext,
    ProtocolArtifact,
    ProtocolClause,
)
from core.phase3_revision_engine.verifier import IotaVerifier

ROOT = Path(__file__).resolve().parents[1]
DEMO_PATH = ROOT / "demo" / "iota_verbum_e2e.html"


def _rejection(code: str, message: str = "Residual_Support") -> dict[str, object]:
    return {
        "source_rejection_id": "rejection:test",
        "code": code,
        "candidate_id": "candidate:test",
        "candidate_kind": "revision_delta",
        "path": "/operations/0",
        "message": message,
        "attempt_index": 1,
    }


def _graphs() -> tuple[dict[str, object], dict[str, object]]:
    prior = {
        "prior_claim_ids": ["claim:target"],
        "preserved_claim_ids": ["claim:stable"],
    }
    trigger = {
        "trigger_claim_ids": ["claim:target"],
        "evidence_ids": ["ev:trigger"],
        "support_edges": [["ev:trigger", "claim:target", "grounds"]],
    }
    return prior, trigger


def test_sealed_doctrine_context_hash_and_thresholds_are_single_source() -> None:
    assert isinstance(SEALED_DOCTRINE, DoctrineContext)
    assert SEALED_DOCTRINE.retract_threshold == 0.30
    assert SEALED_DOCTRINE.collapse_residual_max == 0.05
    assert SEALED_DOCTRINE.seal_hash() == SEALED_DOCTRINE.seal_hash()
    verifier = IotaVerifier()
    assert verifier.doctrine_context is SEALED_DOCTRINE
    source = inspect.getsource(IotaVerifier)
    assert "self.doctrine_context.retract_threshold" in source
    assert "before > 0.30" not in source


def test_repair_guidance_complete_and_schema_conflict_branches_used() -> None:
    expected = set(SEALED_DOCTRINE.doctrine_families) | {
        "__SCHEMA__",
        "__CONFLICT__",
        "__FALLBACK__",
    }
    assert set(REPAIR_GUIDANCE) == expected

    prior, trigger = _graphs()
    schema_result = diagnose_rejection(
        rejection=_rejection("invalid_structure", "wrong operation_type"),
        prior_graph=prior,
        trigger_graph=trigger,
        operation={"operation_id": "op:schema"},
    )
    assert schema_result.repair_instruction is not None
    assert schema_result.repair_instruction.guidance == REPAIR_GUIDANCE["__SCHEMA__"]

    conflict_result = diagnose_rejection(
        rejection=_rejection("operation_conflict", "two non-preserve operations"),
        prior_graph=prior,
        trigger_graph=trigger,
        operation={"operation_id": "op:conflict"},
    )
    assert conflict_result.repair_instruction is not None
    assert (
        conflict_result.repair_instruction.guidance
        == REPAIR_GUIDANCE["__CONFLICT__"]
    )


def test_session_ledger_and_trust_chain_carry_doctrine_context() -> None:
    ledger = SessionLedger()
    session_id = ledger.open_session(
        model_id="model:test",
        model_version="2026-06-01",
        generation_params={"temperature": 0},
        case_id="case:test",
    )
    record = ledger.get_session(session_id)
    assert record.doctrine_context is SEALED_DOCTRINE
    assert record.doctrine_version == SEALED_DOCTRINE.doctrine_version
    assert record.doctrine_digest == SEALED_DOCTRINE.doctrine_digest
    assert record.doctrine_seal == SEALED_DOCTRINE.seal_hash()

    chain = build_trust_chain(session_record=record)
    assert isinstance(chain, TrustChain)
    assert chain.doctrine_context is SEALED_DOCTRINE
    assert chain.doctrine_seal == SEALED_DOCTRINE.seal_hash()

    tampered = type(record)(
        **{**record.__dict__, "doctrine_seal": "tampered"}
    )
    with pytest.raises(AssertionError):
        build_trust_chain(session_record=tampered)


def test_protocol_artifact_types_live_in_types_not_synthesis_module() -> None:
    import core.phase3_revision_engine.certificates.protocol_artifact as module

    source = inspect.getsource(module)
    assert ProtocolClause.__module__ == "core.phase3_revision_engine.types"
    assert ProtocolArtifact.__module__ == "core.phase3_revision_engine.types"
    assert "@dataclass" not in source
    assert "class ProtocolArtifact" not in source
    assert "class ProtocolClause" not in source


def test_e2e_demo_contains_diff_viewer_and_pure_apply_delta_contract() -> None:
    html = DEMO_PATH.read_text(encoding="utf-8")
    assert "const SEALED_DOCTRINE = Object.freeze" in html
    assert "retract_threshold: 0.30" in html
    assert "collapse_residual_max: 0.05" in html
    assert "class IotaVerifier" in html
    assert "this.doctrine.retract_threshold" in html
    assert "before > 0.30" not in html
    assert '<div class="edv-panel" id="edv-prior">' in html
    assert '<div class="edv-panel" id="edv-trigger">' in html
    assert '<div class="edv-panel" id="edv-delta">' in html
    assert 'edv-panel edv-committed hidden" id="edv-committed"' in html
    assert "function renderEpistemicDiff" in html
    assert "function overlayVerifierRejection" in html
    assert "function overlayVerifierAccepted" in html
    assert "function renderCommittedGraph" in html
    assert "function applyDelta" in html
    assert "const postGraph = {" in html
    assert ".edv-invalidated" in html
    assert "INVALIDATED" in html
    assert 'emitEvent("PROPOSED_DELTA"' in html
    assert 'emitEvent("VERIFIER_RESULT"' in html
    assert 'emitEvent("ACCEPTED"' in html
