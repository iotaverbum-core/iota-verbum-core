import json
from pathlib import Path

from deterministic_ai import main


def test_legal_contract_extraction(tmp_path: Path):
    out_dir = tmp_path / "legal"
    main(
        [
            "--domain",
            "legal_contract",
            "--input-ref",
            "sample_contract",
            "--input-file",
            "data/legal_contract_sample/sample_contract.txt",
            "--timestamp",
            "2026-02-28T14:32:00Z",
            "--commit-ref",
            "e20fbd8",
            "--repo-tag",
            "v0.2.0-legal-domain",
            "--out",
            str(out_dir),
        ]
    )

    output = json.loads((out_dir / "output.json").read_text(encoding="utf-8"))
    extraction = output["extraction"]
    assert output["domain"] == "legal_contract"
    assert extraction["effective_date"] == "2024-01-15"
    assert extraction["term"]["end"] == "2025-01-14"
    assert len(extraction["parties"]) == 2
    assert len(extraction["obligations"]) >= 4
    assert extraction["defined_terms"]["Software"].startswith(
        "the hosted workflow orchestration platform"
    )
    assert extraction["governing_law"]["jurisdiction"] == "the State of Delaware"
    assert extraction["termination_conditions"]
    assert extraction["extraction_warnings"] == []


def test_sample_contract_manifest_matches_input():
    manifest_text = Path("data/legal_contract_sample/manifest.sha256").read_text(
        encoding="utf-8"
    )
    payload = Path("data/legal_contract_sample/sample_contract.txt").read_bytes()
    expected = manifest_text.split("  ", 1)[0]
    import hashlib

    actual = hashlib.sha256(payload).hexdigest()
    assert actual == expected
