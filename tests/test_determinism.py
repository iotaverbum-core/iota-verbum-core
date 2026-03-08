from core.determinism.canonical_json import dumps_canonical
from core.engine import run_narrative_intelligence_v2
from proposal.evidence_pack import build_evidence_pack


def test_v2_pipeline_byte_determinism(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "case.txt").write_text(
        "2026-01-01 Ops approved transfer.\n"
        "2026-01-02 Team escalated fraud alert.\n"
        "Policy should be enforced.\n",
        encoding="utf-8",
    )
    pack, _ = build_evidence_pack(str(docs), root_hint="docs")
    config = {"mode": "deterministic", "schema_version": "2.0", "timestamp": "fixed"}
    first = run_narrative_intelligence_v2(pack, config)
    second = run_narrative_intelligence_v2(pack, config)
    assert dumps_canonical(first) == dumps_canonical(second)
