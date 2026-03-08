from core.engine import run_narrative_intelligence_v2
from proposal.evidence_pack import build_evidence_pack


def test_identity_engine_emits_ranked_candidates(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "case.txt").write_text(
        "2026-01-01 fraud transfer detected and escalated.\n", encoding="utf-8"
    )
    pack, _ = build_evidence_pack(str(docs), root_hint="docs")
    result = run_narrative_intelligence_v2(pack, {"mode": "deterministic"})
    assert result["identity"]["candidates"]
    assert (
        result["identity"]["candidates"][0]["confidence"]
        >= result["identity"]["candidates"][-1]["confidence"]
    )
