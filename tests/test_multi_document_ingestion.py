from __future__ import annotations

from pathlib import Path

from core.determinism.finalize import finalize
from core.determinism.ledger import write_run
from core.determinism.replay import verify_run
from proposal.bundle_from_pack import build_evidence_bundle_from_pack
from proposal.evidence_pack import build_evidence_pack


def _write_docs(base: Path) -> None:
    (base / "b.txt").write_text(
        "Incident Report\n\n## Timeline\n- breach detected",
        encoding="utf-8",
    )
    (base / "a.md").write_text(
        "# Access Policy\n\n## Requirements\n- MFA required",
        encoding="utf-8",
    )


def test_deterministic_corpus_ordering(tmp_path: Path) -> None:
    d1 = tmp_path / "left"
    d2 = tmp_path / "right"
    d1.mkdir()
    d2.mkdir()
    _write_docs(d1)
    _write_docs(d2)

    p1, b1 = build_evidence_pack(str(d1), extract_structure=True, categorize=True)
    p2, b2 = build_evidence_pack(str(d2), extract_structure=True, categorize=True)

    assert b1 == b2
    assert p1["pack_sha256"] == p2["pack_sha256"]


def test_multi_document_manifest_and_chunk_metadata(tmp_path: Path) -> None:
    d = tmp_path / "docs"
    d.mkdir()
    _write_docs(d)
    pack, _ = build_evidence_pack(str(d), extract_structure=True, categorize=True)

    assert pack["corpus_manifest"]["total_docs"] == 2
    assert all("title" in item for item in pack["corpus_manifest"]["documents"])
    assert all("heading_path" in chunk for chunk in pack["chunks"])


def test_heading_extraction_is_deterministic(tmp_path: Path) -> None:
    d = tmp_path / "docs"
    d.mkdir()
    (d / "doc.md").write_text(
        "Main Title\n====\n\n1. Overview\nBody",
        encoding="utf-8",
    )
    pack, _ = build_evidence_pack(str(d), extract_structure=True)
    structure = pack["document_structure"][0]
    assert structure["title"] == "Main Title"
    assert any("Overview" in item for item in structure["headings"])


def test_section_aware_chunking_preserves_heading_path(tmp_path: Path) -> None:
    d = tmp_path / "docs"
    d.mkdir()
    (d / "doc.md").write_text("# T\n\n## H1\n" + ("alpha " * 120), encoding="utf-8")
    pack, _ = build_evidence_pack(
        str(d),
        extract_structure=True,
        chunk_target_words=40,
        chunk_overlap_words=10,
    )
    assert len(pack["chunks"]) >= 2
    assert all(chunk["heading_path"] for chunk in pack["chunks"])


def test_category_inference_stable_and_sorted(tmp_path: Path) -> None:
    d = tmp_path / "docs"
    d.mkdir()
    (d / "doc.md").write_text(
        "# Policy\n\nRunbook control policy standard",
        encoding="utf-8",
    )
    pack, _ = build_evidence_pack(str(d), extract_structure=True, categorize=True)
    categories = pack["document_structure"][0]["categories"]
    assert "policy" in categories
    assert pack["document_structure"][0]["category_receipts"]


def test_large_corpus_respects_limits(tmp_path: Path) -> None:
    d = tmp_path / "docs"
    d.mkdir()
    for i in range(30):
        (d / f"doc_{i:03d}.txt").write_text(
            f"Doc {i}\n\n" + ("word " * 200),
            encoding="utf-8",
        )
    pack, _ = build_evidence_pack(
        str(d),
        extract_structure=True,
        max_docs=10,
        max_total_chunks=20,
    )
    assert len(pack["documents"]) == 10
    assert len(pack["chunks"]) <= 20


def test_replay_compatibility_with_upgraded_pack(tmp_path: Path) -> None:
    d = tmp_path / "docs"
    d.mkdir()
    _write_docs(d)
    pack, _ = build_evidence_pack(str(d), extract_structure=True, categorize=True)
    bundle_obj, _, _ = build_evidence_bundle_from_pack(
        pack,
        prompt="p",
        params={"mode": "all"},
        created_utc="2026-03-08T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
    )
    sealed = finalize(
        bundle_obj,
        {"ok": True},
        manifest_sha256="0" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-08T12:00:00Z",
    )
    ledger = write_run(ledger_root=str(tmp_path / "ledger"), **sealed)
    result = verify_run(ledger)
    assert result["ok"] is True


def test_backward_compatible_single_document_flow(tmp_path: Path) -> None:
    d = tmp_path / "docs"
    d.mkdir()
    (d / "doc.txt").write_text("abcdefghij", encoding="utf-8")
    pack, _ = build_evidence_pack(str(d), max_chars=4, overlap_chars=1)
    assert [chunk["text"] for chunk in pack["chunks"]] == ["abcd", "defg", "ghij"]
    assert all(chunk["section_id"] == "" for chunk in pack["chunks"])
