import json
from pathlib import Path

import pytest

from core.determinism.finalize import finalize
from core.determinism.hashing import sha256_bytes
from core.determinism.ledger import write_run
from core.determinism.replay import verify_run

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
