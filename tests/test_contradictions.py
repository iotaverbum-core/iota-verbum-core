from core.engine import run_narrative_intelligence_v2
from proposal.evidence_pack import build_evidence_pack


def test_contradictions_reports_insufficiency_when_unknowns_present(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "case.txt").write_text(
        "Transfer approved without time should be documented.\n", encoding="utf-8"
    )
    pack, _ = build_evidence_pack(str(docs), root_hint="docs")
    result = run_narrative_intelligence_v2(pack, {"mode": "deterministic"})
    classes = {c["class"] for c in result["contradictions"]["contradictions"]}
    assert "evidentiary_insufficiency" in classes
