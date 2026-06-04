from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import scripts.build_phase3_customer_evidence as evidence_builder
from scripts.build_phase3_customer_evidence import build_customer_evidence_package
from scripts.delta_gap_diagnostic import compare_deltas

from core.cuc_harness.deepseek_proposer import RevisionDelta
from core.cuc_harness.ledger_commit import commit_verified_revision_delta
from core.cuc_harness.verifier import verify_revision_delta

pytestmark = pytest.mark.timeout(30)

CASE_ID = "CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
SOURCE_CASE_ID = "CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
FIXTURE_DIR = Path("benchmark/kaggle/fixtures") / SOURCE_CASE_ID


def test_build_customer_evidence_package_replays_and_avoids_overclaim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_root = _write_session(tmp_path)
    scorecard_source = session_root / CASE_ID / "scorecard.json"
    scorecard_source.write_bytes(scorecard_source.read_bytes().replace(b"\n", b"\r\n"))
    package_dir = tmp_path / "package"
    package_dir.mkdir()
    sealed_manifest = Path("MANIFEST.sha256").resolve()
    monkeypatch.setattr(
        evidence_builder,
        "_manifest_at_commit",
        lambda _commit_sha: sealed_manifest.read_bytes(),
    )
    monkeypatch.chdir(tmp_path)

    report = build_customer_evidence_package(
        session_root=session_root,
        case_id=CASE_ID,
        sealed_manifest=sealed_manifest,
        sealed_repository_commit="1" * 40,
        package_dir=Path("package"),
    )

    assert report["evidence_status"] == "strict_replay_verified"
    assert report["session_result"]["similarity_before"] < 100.0
    assert report["session_result"]["similarity_after"] == 100.0
    assert report["session_result"]["training_pass_count"] == 1
    assert report["strict_replay"]["ok"] is True
    assert report["strict_replay"]["warnings"] == []
    assert report["sealed_repository_manifest_verified"] is True
    assert report["packaged_delta_ledger_match_verified"] is True
    assert "persistent weight-level model improvement" in report["proof_boundary"]
    assert (
        package_dir / "MANIFEST.sha256"
    ).read_bytes() == sealed_manifest.read_bytes()
    assert (
        package_dir / "ledger" / report["ledger_attestation"]["bundle_sha256"]
    ).is_dir()
    for artifact in report["artifact_hashes"]:
        packaged_bytes = (package_dir / artifact["path"]).read_bytes()
        assert hashlib.sha256(packaged_bytes).hexdigest() == artifact["sha256"]
        assert len(packaged_bytes) == artifact["bytes"]
    assert b"\r\n" not in (package_dir / "evidence" / "scorecard.json").read_bytes()

    markdown = (package_dir / "customer_evidence_report.md").read_text(
        encoding="utf-8"
    )
    assert f"{report['session_result']['similarity_before']:.2f}%" in markdown
    assert "100.00%" in markdown
    assert "strict-manifest" in markdown
    assert tmp_path.as_posix() not in markdown


def test_build_customer_evidence_package_rejects_stale_failure(
    tmp_path: Path,
) -> None:
    session_root = _write_session(tmp_path)
    pass_dir = session_root / "passes" / "pass_001" / CASE_ID
    _write_json(pass_dir / "retry_failure.json", {"error_type": "stale"})

    with pytest.raises(ValueError, match="retry_failure"):
        build_customer_evidence_package(
            session_root=session_root,
            case_id=CASE_ID,
            sealed_manifest=Path("MANIFEST.sha256"),
            sealed_repository_commit="1" * 40,
            package_dir=tmp_path / "package",
        )


def test_build_customer_evidence_package_rejects_uncommitted_retry_delta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_root = _write_session(tmp_path)
    retry_delta_path = (
        session_root / "passes" / "pass_001" / CASE_ID / "retry_model_delta.json"
    )
    retry_delta = _read_json(retry_delta_path)
    retry_delta["revision_notes"] = "Tampered after ledger commit."
    _write_json(retry_delta_path, retry_delta)
    sealed_manifest = Path("MANIFEST.sha256").resolve()
    monkeypatch.setattr(
        evidence_builder,
        "_manifest_at_commit",
        lambda _commit_sha: sealed_manifest.read_bytes(),
    )

    with pytest.raises(
        ValueError,
        match="packaged retry_model_delta.json does not match ledger output delta",
    ):
        build_customer_evidence_package(
            session_root=session_root,
            case_id=CASE_ID,
            sealed_manifest=sealed_manifest,
            sealed_repository_commit="1" * 40,
            package_dir=tmp_path / "package",
        )


def _write_session(tmp_path: Path) -> Path:
    clean_pack = _read_json(FIXTURE_DIR / "clean_pack.json")
    perturbed_pack = _read_json(FIXTURE_DIR / "perturbed_pack.json")
    expected_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    rejected_delta = json.loads(json.dumps(expected_delta))
    rejected_delta["changed_states"] = [
        item
        for item in rejected_delta["changed_states"]
        if item["id"] != "state:primary"
    ]
    rejected_delta["supporting_evidence_map"].pop("scenario:primary", None)

    baseline = RevisionDelta.model_validate(rejected_delta)
    accepted = RevisionDelta.model_validate(expected_delta)
    baseline_verification = verify_revision_delta(baseline, expected_delta)
    accepted_verification = verify_revision_delta(accepted, expected_delta)
    baseline_gap = compare_deltas(rejected_delta, expected_delta).to_dict()
    accepted_gap = compare_deltas(expected_delta, expected_delta).to_dict()

    session_root = tmp_path / "session"
    pass_dir = session_root / "passes" / "pass_001" / CASE_ID
    pass_dir.mkdir(parents=True)
    commit = commit_verified_revision_delta(
        case_id=CASE_ID,
        model="deepseek-v4-pro",
        clean_pack=clean_pack,
        perturbed_pack=perturbed_pack,
        expected_delta=expected_delta,
        delta=accepted,
        verification=accepted_verification,
        ledger_root=session_root / "ledger",
        created_utc="2026-06-04T00:00:00Z",
    ).to_dict()

    _write_json(pass_dir / "baseline_gap_report.json", baseline_gap)
    _write_json(pass_dir / "baseline_model_delta.json", rejected_delta)
    _write_json(
        pass_dir / "baseline_verification.json",
        baseline_verification.to_dict(),
    )
    _write_json(
        pass_dir / "repair_instruction.json",
        {
            "candidate_kind": "repair_instruction",
            "case_id": CASE_ID,
            "failure_family": "GROUNDING_GAP",
            "target_operation_id": "multiple",
            "repair_template": "Patch only the cited grounding gap.",
            "grounding_evidence_ids": ["evidence:primary"],
            "preservation_constraints": ["state:secondary"],
        },
    )
    _write_json(pass_dir / "retry_gap_report.json", accepted_gap)
    _write_json(pass_dir / "retry_model_delta.json", expected_delta)
    _write_json(pass_dir / "verification.json", accepted_verification.to_dict())
    _write_json(
        pass_dir / "training_summary.json",
        {
            "retry": {
                "called": True,
                "json_valid": True,
                "accepted": True,
                "ledger_committed": True,
                "ledger_commit": commit,
            },
            "no_regression_guard": {
                "selected_candidate": "retry",
                "retry_improved": True,
                "retry_regressed": False,
            },
        },
    )

    scorecard = {
        "schema_version": "iv.phase3.training_room_wrapper.v1",
        "service_kind": "iota_training_room",
        "provider": "deepseek",
        "case_id": CASE_ID,
        "source_case_id": SOURCE_CASE_ID,
        "allow_live_model": True,
        "stop_reason": "accepted",
        "baseline": {
            "accepted": False,
            "similarity_score_percent": baseline_gap["summary"][
                "similarity_score_percent"
            ],
        },
        "best_candidate": {
            "accepted": True,
            "similarity_score_percent": 100.0,
            "ledger_committed": True,
            "ledger_commit": commit,
        },
        "training_effect": {
            "accepted_before": False,
            "accepted_after": True,
            "improved": True,
            "similarity_before": baseline_gap["summary"][
                "similarity_score_percent"
            ],
            "similarity_after": 100.0,
            "similarity_delta": round(
                100.0 - baseline_gap["summary"]["similarity_score_percent"],
                2,
            ),
            "verifier_reason_count_before": len(baseline_verification.reasons),
            "verifier_reason_count_after": 0,
        },
        "training_passes": [
            {
                "pass_index": 1,
                "called": True,
                "accepted": True,
                "ledger_committed": True,
                "selected_candidate": "retry",
                "retry_regressed": False,
            }
        ],
    }
    scorecard_dir = session_root / CASE_ID
    scorecard_dir.mkdir(parents=True)
    _write_json(scorecard_dir / "scorecard.json", scorecard)
    return session_root


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
