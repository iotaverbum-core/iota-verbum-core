from __future__ import annotations

import json
from pathlib import Path

from core.cuc_harness.deepseek_proposer import RevisionDelta
from core.cuc_harness.verifier import verify_revision_delta

FIXTURE_DIR = Path(
    "benchmark/kaggle/fixtures/"
    "CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
)


def test_verify_revision_delta_accepts_expected_delta() -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    proposal = RevisionDelta.model_validate(gold_delta)

    verification = verify_revision_delta(proposal, gold_delta)

    assert verification.accepted
    assert verification.reasons == []
    assert verification.reason_families == []
    assert verification.to_dict() == {
        "accepted": True,
        "reasons": [],
        "reason_families": [],
    }


def test_verify_revision_delta_reports_stable_reason_families() -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    proposal_payload = json.loads(json.dumps(gold_delta))
    proposal_payload["changed_states"] = []
    proposal_payload["preserved_items"] = []
    proposal_payload["named_evidence_artifact"] = "wrong-artifact"

    verification = verify_revision_delta(proposal_payload, gold_delta)

    assert not verification.accepted
    assert verification.reason_families == [
        "missing_changed_states",
        "missing_preserved_items",
        "named_evidence_artifact_mismatch",
    ]
    assert any(
        reason.startswith("missing_changed_states:")
        for reason in verification.reasons
    )
    assert any(
        reason.startswith("missing_preserved_items:")
        for reason in verification.reasons
    )
    assert (
        "named_evidence_artifact_mismatch:"
        "wrong-artifact!=evidence:corroboration"
    ) in verification.reasons


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
