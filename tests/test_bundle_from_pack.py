from pathlib import Path

from core.determinism.bundle import build_evidence_bundle
from core.determinism.hashing import sha256_text
from proposal.bundle_from_pack import build_evidence_bundle_from_pack
from proposal.evidence_pack import build_evidence_pack


def _build_pack(sample_dir: Path) -> dict:
    pack_obj, _ = build_evidence_pack(
        str(sample_dir),
        root_hint="docs",
        max_chars=80,
        overlap_chars=10,
    )
    return pack_obj


def test_build_bundle_from_pack_is_byte_identical(tmp_path: Path):
    sample_dir = tmp_path / "docs"
    sample_dir.mkdir()
    (sample_dir / "a.md").write_text("# Topic\n- Alpha keyword\n", encoding="utf-8")
    (sample_dir / "b.md").write_text("# Other\n- Beta keyword\n", encoding="utf-8")
    pack = _build_pack(sample_dir)

    left = build_evidence_bundle_from_pack(
        pack,
        prompt="Summarize keyword",
        params={"mode": "all"},
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        mode="all",
    )
    right = build_evidence_bundle_from_pack(
        pack,
        prompt="Summarize keyword",
        params={"mode": "all"},
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        mode="all",
    )

    assert left[1] == right[1]
    assert left[2] == right[2]


def test_keyword_and_topk_selection_are_stable(tmp_path: Path):
    sample_dir = tmp_path / "docs"
    sample_dir.mkdir()
    (sample_dir / "a.md").write_text("# Topic\n- Alpha keyword\n", encoding="utf-8")
    (sample_dir / "b.md").write_text("# Other\n- keyword keyword\n", encoding="utf-8")
    pack = _build_pack(sample_dir)

    keyword_bundle = build_evidence_bundle_from_pack(
        pack,
        prompt="Summarize keyword",
        params={},
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        mode="keyword",
        query="keyword",
        max_chunks=10,
    )[0]
    topk_bundle = build_evidence_bundle_from_pack(
        pack,
        prompt="Summarize keyword",
        params={},
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        mode="topk",
        query="keyword",
        max_chunks=1,
    )[0]

    keyword_sources = [
        artifact["source_id"]
        for artifact in keyword_bundle["artifacts"]
    ]
    assert keyword_sources == sorted(
        [
            pack["documents"][0]["doc_id"],
            pack["documents"][1]["doc_id"],
        ]
    )
    assert [artifact["source_id"] for artifact in topk_bundle["artifacts"]] == [
        pack["documents"][1]["doc_id"]
    ]


def test_artifact_hashes_match_and_bundle_validates(tmp_path: Path):
    sample_dir = tmp_path / "docs"
    sample_dir.mkdir()
    (sample_dir / "a.md").write_text("# Topic\n- Alpha\n", encoding="utf-8")
    pack = _build_pack(sample_dir)

    bundle_obj, bundle_bytes, bundle_sha256 = build_evidence_bundle_from_pack(
        pack,
        prompt="Summarize",
        params={"x": 1},
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
    )

    for artifact in bundle_obj["artifacts"]:
        assert artifact["text_sha256"] == sha256_text(artifact["text"])

    rebuilt_bytes, rebuilt_sha256 = build_evidence_bundle(bundle_obj)
    assert bundle_bytes == rebuilt_bytes
    assert bundle_sha256 == rebuilt_sha256
