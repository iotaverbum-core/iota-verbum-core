import json
import logging
from pathlib import Path

import pytest

from core.determinism.finalize import finalize
from core.determinism.hashing import sha256_bytes
from core.determinism.ledger import write_run
from core.determinism.replay import verify_run, verify_run_deterministic

FIXTURES = Path("tests/fixtures")


def _bundle() -> dict:
    return json.loads(
        (FIXTURES / "evidence_bundle_example.json").read_text(encoding="utf-8")
    )


def _sealed(manifest_sha256: str) -> dict:
    return finalize(
        _bundle(),
        {"decision": "allow", "reasons": ["matched"]},
        manifest_sha256=manifest_sha256,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
    )


def test_verify_run_returns_ok_true(tmp_path: Path):
    manifest_sha256 = sha256_bytes(Path("MANIFEST.sha256").read_bytes())
    sealed = _sealed(manifest_sha256)
    run_dir = write_run(ledger_root=str(tmp_path), **sealed)

    result = verify_run(str(run_dir))

    assert result["ok"] is True
    assert result["bundle_sha256"] == sealed["bundle_sha256"]
    assert result["output_sha256"] == sealed["output_sha256"]
    assert result["attestation_sha256"] == sealed["attestation_sha256"]
    assert result["warnings"] == []


def test_verify_run_warns_when_manifest_mismatch_if_not_strict(tmp_path: Path):
    sealed = _sealed("1" * 64)
    run_dir = write_run(ledger_root=str(tmp_path), **sealed)

    result = verify_run(str(run_dir), strict_manifest=False)

    assert result["ok"] is True
    assert result["warnings"] == ["manifest_sha256 mismatch"]


def test_verify_run_raises_when_manifest_mismatch_if_strict(tmp_path: Path):
    sealed = _sealed("1" * 64)
    run_dir = write_run(ledger_root=str(tmp_path), **sealed)

    with pytest.raises(ValueError, match="manifest_sha256 mismatch"):
        verify_run(str(run_dir), strict_manifest=True)


def test_verify_run_deterministic_skips_when_no_comparable_artifacts(tmp_path: Path):
    run_dir = tmp_path / "run-empty" / "ledger" / ("a" * 64)
    run_dir.mkdir(parents=True, exist_ok=True)

    result = verify_run_deterministic(str(run_dir), strict_manifest=True)

    assert result["ok"] is False
    assert result["status"] == "skipped"
    assert result["reason"] == "no comparable replay artifacts found"
    assert result["empty_collection"] == "comparable_artifacts"
    assert result["sub_step"] == "artifact_discovery"


def test_verify_run_deterministic_logs_empty_collection_details(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    run_dir = tmp_path / "run-log" / "ledger" / ("b" * 64)
    run_dir.mkdir(parents=True, exist_ok=True)
    caplog.set_level(logging.WARNING)

    verify_run_deterministic(str(run_dir), strict_manifest=True)

    assert any(
        "run_id=run-log" in record.message
        and "sub_step=artifact_discovery" in record.message
        and "empty_collection=comparable_artifacts" in record.message
        for record in caplog.records
    )


def test_verify_run_deterministic_fails_when_manifest_entries_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    manifest_sha256 = sha256_bytes(Path("MANIFEST.sha256").read_bytes())
    sealed = _sealed(manifest_sha256)
    run_dir = write_run(ledger_root=str(tmp_path), **sealed)
    manifest_root = tmp_path / "manifest-empty"
    manifest_root.mkdir(parents=True, exist_ok=True)
    (manifest_root / "MANIFEST.sha256").write_text("", encoding="utf-8")
    monkeypatch.chdir(manifest_root)

    result = verify_run_deterministic(str(run_dir), strict_manifest=True)

    assert result["ok"] is False
    assert result["status"] == "failed_deterministically"
    assert result["reason"] == "no comparable replay artifacts found"
    assert result["empty_collection"] == "manifest_entries"
    assert result["sub_step"] == "manifest_compare"


def test_verify_run_deterministic_fails_when_output_file_missing(tmp_path: Path):
    manifest_sha256 = sha256_bytes(Path("MANIFEST.sha256").read_bytes())
    sealed = _sealed(manifest_sha256)
    run_dir = Path(write_run(ledger_root=str(tmp_path), **sealed))
    (run_dir / "output.json").unlink()

    result = verify_run_deterministic(str(run_dir), strict_manifest=True)

    assert result["ok"] is False
    assert result["status"] == "failed_deterministically"
    assert result["reason"].startswith("missing required replay artifacts:")
    assert result["empty_collection"] == "required_replay_artifacts"
    assert result["missing_artifacts"] == ["output.json"]


def test_verify_run_raises_structured_failure_for_empty_artifacts(tmp_path: Path):
    run_dir = tmp_path / "run-raise" / "ledger" / ("c" * 64)
    run_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match="no comparable replay artifacts found"):
        verify_run(str(run_dir), strict_manifest=True)
