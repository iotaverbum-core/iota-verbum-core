from __future__ import annotations

import json
from pathlib import Path

from core.cuc_harness.deepseek_proposer import RevisionDelta
from core.cuc_harness.ledger_commit import (
    CUC_LEDGER_OUTPUT_SCHEMA_VERSION,
    build_cuc_evidence_bundle,
    commit_verified_revision_delta,
)
from core.cuc_harness.verifier import verify_revision_delta


FIXTURE_DIR = Path(
    "benchmark/kaggle/fixtures/"
    "CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
)


def test_build_cuc_evidence_bundle_uses_core_evidence_bundle_shape() -> None:
    clean_pack = _read_json(FIXTURE_DIR / "clean_pack.json")
    perturbed_pack = _read_json(FIXTURE_DIR / "perturbed_pack.json")
    expected_delta = _read_json(FIXTURE_DIR / "expected_delta.json")

    bundle = build_cuc_evidence_bundle(
        case_id="CASE-001",
        model="claude-sonnet-4-6",
        clean_pack=clean_pack,
        perturbed_pack=perturbed_pack,
        expected_delta=expected_delta,
        created_utc="2026-05-27T00:00:00Z",
    )

    assert bundle["bundle_version"] == "1.0"
    assert bundle["inputs"]["prompt"] == "CUC structured RevisionDelta proposal"
    assert bundle["inputs"]["params"]["case_id"] == "CASE-001"
    assert [artifact["chunk_id"] for artifact in bundle["artifacts"]] == [
        "clean_pack",
        "perturbed_pack",
        "expected_delta",
    ]


def test_commit_verified_revision_delta_writes_ledger_run(tmp_path: Path) -> None:
    clean_pack = _read_json(FIXTURE_DIR / "clean_pack.json")
    perturbed_pack = _read_json(FIXTURE_DIR / "perturbed_pack.json")
    expected_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    proposal = RevisionDelta.model_validate(expected_delta)
    verification = verify_revision_delta(proposal, expected_delta)

    commit = commit_verified_revision_delta(
        case_id="CASE-001",
        model="claude-sonnet-4-6",
        clean_pack=clean_pack,
        perturbed_pack=perturbed_pack,
        expected_delta=expected_delta,
        delta=proposal,
        verification=verification,
        ledger_root=tmp_path / "ledger",
        created_utc="2026-05-27T00:00:00Z",
    )

    assert commit.run_dir.is_dir()
    output = json.loads((commit.run_dir / "output.json").read_text(encoding="utf-8"))
    assert output["schema_version"] == CUC_LEDGER_OUTPUT_SCHEMA_VERSION
    assert output["verifier"]["accepted"] is True
    assert (commit.run_dir / "bundle.json").is_file()
    assert (commit.run_dir / "attestation.json").is_file()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
