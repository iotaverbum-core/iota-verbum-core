import json
from pathlib import Path

import pytest

from core.determinism.finalize import finalize
from core.determinism.ledger import write_run

FIXTURES = Path("tests/fixtures")


def _bundle() -> dict:
    return json.loads(
        (FIXTURES / "evidence_bundle_example.json").read_text(encoding="utf-8")
    )


def _sealed(manifest_sha256: str = "1" * 64) -> dict:
    return finalize(
        _bundle(),
        {"decision": "allow", "evidence_count": 2},
        manifest_sha256=manifest_sha256,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
    )


def test_write_run_writes_expected_files(tmp_path: Path):
    sealed = _sealed()

    run_dir = write_run(ledger_root=str(tmp_path), **sealed)

    assert run_dir.is_dir()
    assert (run_dir / "bundle.json").read_bytes() == sealed["bundle_bytes"]
    assert (run_dir / "output.json").read_bytes() == sealed["output_bytes"]
    assert (run_dir / "attestation.json").read_bytes() == sealed["attestation_bytes"]


def test_write_run_is_idempotent_for_identical_inputs(tmp_path: Path):
    sealed = _sealed()

    first = write_run(ledger_root=str(tmp_path), **sealed)
    second = write_run(ledger_root=str(tmp_path), **sealed)

    assert first == second
    assert (first / "bundle.json").read_bytes() == sealed["bundle_bytes"]


def test_write_run_raises_on_existing_content_mismatch(tmp_path: Path):
    sealed = _sealed()
    write_run(ledger_root=str(tmp_path), **sealed)

    mutated = finalize(
        _bundle(),
        {"decision": "deny", "evidence_count": 2},
        manifest_sha256="1" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
    )

    with pytest.raises(ValueError, match="existing ledger file mismatch"):
        write_run(ledger_root=str(tmp_path), **mutated)
