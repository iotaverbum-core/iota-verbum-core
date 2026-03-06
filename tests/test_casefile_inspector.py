from __future__ import annotations

import json
from pathlib import Path

from core.casefile.inspect import main as inspect_main


def _valid_casefile() -> dict:
    return {
        "casefile_version": "1.0",
        "casefile_id": "case:" + ("1" * 64),
        "created_utc": "2026-03-06T10:00:00Z",
        "core_version": "0.4.0",
        "ruleset_id": "ruleset.core.v1",
        "query": "q",
        "prompt": "p",
        "hashes": {
            "manifest_sha256": "2" * 64,
            "bundle_sha256": "3" * 64,
            "world_sha256": "4" * 64,
            "output_sha256": "5" * 64,
            "attestation_sha256": "6" * 64,
        },
        "ledger_dir": "outputs/demo/run/ledger/" + ("7" * 64),
        "summary": {
            "entities": 2,
            "events": 3,
            "unknowns": 0,
            "conflicts": 0,
            "verification_status": "VERIFIED_OK",
            "constraint_violations": 0,
            "causal_edges": 5,
        },
        "artifacts": [
            {"name": "attestation.json", "role": "sealed", "sha256": "8" * 64},
            {"name": "bundle.json", "role": "sealed", "sha256": "9" * 64},
            {"name": "output.json", "role": "sealed", "sha256": "a" * 64},
            {
                "name": "casefile.json",
                "role": "derived",
                "sha256": "b" * 64,
                "schema": "schemas/casefile.schema.json",
            },
        ],
        "receipts_summary": {
            "evidence_ref_count": 4,
            "proof_count": 2,
            "finding_count": 1,
        },
    }


def test_casefile_inspector_output_contains_required_labels(
    tmp_path: Path, capsys
) -> None:
    casefile_path = tmp_path / "casefile.json"
    casefile_path.write_text(json.dumps(_valid_casefile()), encoding="utf-8")

    result = inspect_main([str(casefile_path)])
    captured = capsys.readouterr()

    assert result == 0
    for label in (
        "Header",
        "Casefile ID:",
        "Verification Status:",
        "Hashes",
        "manifest_sha256:",
        "Summary",
        "entities:",
        "Ledger",
        "replay command: python -m core.determinism.replay",
        "Artifacts",
        "name | role | sha256 | schema",
        "Receipts",
        "evidence_ref_count:",
        "proof_count:",
        "finding_count:",
    ):
        assert label in captured.out


def test_casefile_inspector_invalid_casefile_exits_nonzero(
    tmp_path: Path, capsys
) -> None:
    bad_casefile = _valid_casefile()
    del bad_casefile["ruleset_id"]
    casefile_path = tmp_path / "invalid_casefile.json"
    casefile_path.write_text(json.dumps(bad_casefile), encoding="utf-8")

    completed = inspect_main([str(casefile_path)])
    captured = capsys.readouterr()

    assert completed != 0
    assert "Casefile inspection failed:" in captured.err


def test_casefile_inspector_missing_file_exits_nonzero(capsys) -> None:
    completed = inspect_main(["missing_casefile.json"])
    captured = capsys.readouterr()

    assert completed != 0
    assert "Casefile inspection failed:" in captured.err
