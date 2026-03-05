from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from proposal.claim_propose import propose_claim_graph
from proposal.evidence_pack import build_evidence_pack


def test_propose_claim_graph_is_deterministic(tmp_path: Path):
    sample_dir = tmp_path / "docs"
    sample_dir.mkdir()
    (sample_dir / "notes.md").write_text(
        "# Topic\n- First point\n- Second point\n",
        encoding="utf-8",
    )

    pack_obj, _ = build_evidence_pack(
        str(sample_dir),
        root_hint="docs",
        max_chars=200,
        overlap_chars=20,
    )

    left = propose_claim_graph(pack_obj)
    right = propose_claim_graph(pack_obj)

    assert dumps_canonical(left) == dumps_canonical(right)
    assert [claim["claim_id"] for claim in left["claims"]] == [
        claim["claim_id"] for claim in right["claims"]
    ]


def test_proposed_claims_include_evidence_refs_matching_pack(tmp_path: Path):
    sample_dir = tmp_path / "docs"
    sample_dir.mkdir()
    (sample_dir / "notes.md").write_text(
        "# Topic\n- First point\n- Second point\n",
        encoding="utf-8",
    )

    pack_obj, _ = build_evidence_pack(
        str(sample_dir),
        root_hint="docs",
        max_chars=200,
        overlap_chars=20,
    )
    graph = propose_claim_graph(pack_obj)
    pack_chunk = pack_obj["chunks"][0]
    pack_doc = pack_obj["documents"][0]

    assert len(graph["claims"]) == 2
    for claim in graph["claims"]:
        assert len(claim["evidence"]) >= 1
        assert claim["evidence"][0] == {
            "source_id": pack_doc["doc_id"],
            "chunk_id": pack_chunk["chunk_id"],
            "offset_start": pack_chunk["offset_start"],
            "offset_end": pack_chunk["offset_end"],
            "text_sha256": pack_chunk["text_sha256"],
        }
        assert claim["claim_id"].startswith("claim:")
