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
    provenance = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    extraction = output["extraction"]
    assert output["domain"] == "legal_contract"
    assert output["schema_version"] == "1.2"
    assert output["review_findings"]
    assert output["review_findings"][0]["finding_class"] == "ambiguity"
    assert output["review_summary"]["status"] == "ready_for_review"
    assert output["review_summary"]["priority"] == "medium"
    assert output["review_summary"]["finding_count"] == len(
        extraction["analysis"]["ambiguities"]
    )
    assert output["review_summary"]["warning_count"] == 0
    assert extraction["effective_date"] == "2024-01-15"
    assert extraction["term"]["end"] == "2025-01-14"
    assert len(extraction["parties"]) == 2
    assert len(extraction["obligations"]) >= 4
    assert extraction["rights"]
    assert extraction["prohibitions"]
    assert extraction["conditional_triggers"]
    assert extraction["defined_terms"]["Software"].startswith(
        "the hosted workflow orchestration platform"
    )
    assert extraction["governing_law"]["jurisdiction"] == "the State of Delaware"
    assert extraction["termination_conditions"]
    assert extraction["analysis"]["contradictions"] == []
    assert extraction["analysis"]["ambiguities"]
    assert extraction["risk_report"]["rights_count"] == len(extraction["rights"])
    assert extraction["extraction_warnings"] == []
    assert provenance["governance_metadata"]["nist_rmf_function"] == "GOVERN"
    assert provenance["neurosymbolic_boundary"]["neural_components_used"] == []


def test_sample_contract_manifest_matches_input():
    manifest_text = Path("data/legal_contract_sample/manifest.sha256").read_text(
        encoding="utf-8"
    )
    payload = Path("data/legal_contract_sample/sample_contract.txt").read_bytes()
    expected = manifest_text.split("  ", 1)[0]
    import hashlib

    actual = hashlib.sha256(payload).hexdigest()
    assert actual == expected


def test_legal_contract_contradiction_analysis(tmp_path: Path):
    contract_text = """
This Software Services Agreement (the "Agreement") is entered into as of January
15, 2024 (the "Effective Date"), by and between Alpha Systems LLC, a Delaware
limited liability company ("Alpha" or "Licensor"), and Beta Operations Inc., an
Oregon corporation ("Beta" or "Licensee").

1. License Grant. Licensor grants Licensee a non-exclusive right to use the
Software for internal business operations. Licensee may use the Software for
internal business operations. Licensee must not use the Software for internal
business operations.

2. Governing Law. This Agreement shall be governed by the laws of the State of Delaware.
""".strip()
    input_path = tmp_path / "conflict_contract.txt"
    input_path.write_text(contract_text, encoding="utf-8")
    out_dir = tmp_path / "legal_conflict"

    main(
        [
            "--domain",
            "legal_contract",
            "--input-ref",
            "conflict_contract",
            "--input-file",
            str(input_path),
            "--timestamp",
            "2026-03-17T12:00:00Z",
            "--commit-ref",
            "abcdef0",
            "--repo-tag",
            "v0.3.0-legal-contradictions",
            "--out",
            str(out_dir),
        ]
    )

    output = json.loads((out_dir / "output.json").read_text(encoding="utf-8"))
    contradictions = output["extraction"]["analysis"]["contradictions"]
    review_findings = output["review_findings"]
    assert len(contradictions) == 1
    contradiction = contradictions[0]
    assert review_findings[0]["finding_class"] == "contradiction"
    assert review_findings[0]["related_party"] == "Beta Operations Inc."
    assert output["review_summary"]["status"] == "review_required"
    assert output["review_summary"]["priority"] == "high"
    assert output["review_summary"]["finding_count"] == 1
    assert contradiction["contradiction_type"] == "RIGHT_PROHIBITION"
    assert contradiction["party"] == "Beta Operations Inc."
    assert contradiction["beneficiary"] == "Beta Operations Inc."
    assert (
        "use the software for internal business operations"
        in contradiction["action"]
    )


def test_legal_contract_prohibition_phrase_is_captured(tmp_path: Path):
    contract_text = """
This Agreement is entered into as of January 15, 2024, by and between Alpha
Systems LLC, a Delaware limited liability company ("Alpha" or "Licensor"), and
Beta Operations Inc., an Oregon corporation ("Beta" or "Licensee").

Licensee is prohibited from sharing administrator credentials with third parties.
This Agreement shall be governed by the laws of the State of Delaware.
""".strip()
    input_path = tmp_path / "prohibition_contract.txt"
    input_path.write_text(contract_text, encoding="utf-8")
    out_dir = tmp_path / "legal_prohibition"

    main(
        [
            "--domain",
            "legal_contract",
            "--input-ref",
            "prohibition_contract",
            "--input-file",
            str(input_path),
            "--timestamp",
            "2026-03-17T12:00:00Z",
            "--commit-ref",
            "abcdef0",
            "--repo-tag",
            "v0.3.0-legal-contradictions",
            "--out",
            str(out_dir),
        ]
    )

    output = json.loads((out_dir / "output.json").read_text(encoding="utf-8"))
    prohibitions = output["extraction"]["prohibitions"]
    assert output["review_summary"]["status"] == "review_required"
    assert any(
        finding["finding_class"] == "warning"
        for finding in output["review_findings"]
    )
    assert len(prohibitions) == 1
    assert prohibitions[0]["party"] == "Beta Operations Inc."
    assert prohibitions[0]["action"].startswith("sharing administrator credentials")
