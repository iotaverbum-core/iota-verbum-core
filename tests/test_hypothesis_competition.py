from core.engine import run_narrative_intelligence_v2
from proposal.evidence_pack import build_evidence_pack


def test_hypothesis_competition_outputs_multiple_rivals(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "case.txt").write_text(
        "2026-01-01 transfer approved. 2026-01-02 fraud escalated.\n", encoding="utf-8"
    )
    pack, _ = build_evidence_pack(str(docs), root_hint="docs")
    result = run_narrative_intelligence_v2(pack, {"mode": "deterministic"})
    hypotheses = result["hypothesis_competition"]["hypotheses"]
    assert len(hypotheses) >= 3
    assert hypotheses == sorted(
        hypotheses, key=lambda h: (-float(h["confidence_score"]), h["hypothesis_id"])
    )
