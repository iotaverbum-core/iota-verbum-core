from core.semantic import extract_semantic_artifacts
from core.world import build_world_graph
from proposal.evidence_pack import build_evidence_pack


def test_world_graph_builds_unknowns_for_missing_time(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "case.txt").write_text(
        "Ops approved transfer without date.\n", encoding="utf-8"
    )
    pack, _ = build_evidence_pack(str(docs), root_hint="docs")
    semantic = extract_semantic_artifacts(pack)
    world = build_world_graph(semantic)
    assert world["entities"]
    assert world["events"]
    assert world["unknowns"]
