from pathlib import Path

from core.determinism.hashing import sha256_text
from proposal.evidence_pack import build_evidence_pack


def test_build_evidence_pack_is_byte_identical_for_identical_inputs(tmp_path: Path):
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "b.md").write_text("Beta\r\nLine\n", encoding="utf-8")
    (sample_dir / "a.md").write_text("Alpha Cafe\u0301\n", encoding="utf-8")

    left_obj, left_bytes = build_evidence_pack(
        str(sample_dir),
        root_hint="sample",
        max_chars=8,
        overlap_chars=2,
    )
    right_obj, right_bytes = build_evidence_pack(
        str(sample_dir),
        root_hint="sample",
        max_chars=8,
        overlap_chars=2,
    )

    assert left_bytes == right_bytes
    assert left_obj["pack_sha256"] == right_obj["pack_sha256"]
    assert [doc["relpath"] for doc in left_obj["documents"]] == ["a.md", "b.md"]


def test_build_evidence_pack_offsets_and_hashes_are_correct(tmp_path: Path):
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    (sample_dir / "doc.md").write_text("abcdefghij", encoding="utf-8")

    pack_obj, _ = build_evidence_pack(
        str(sample_dir),
        max_chars=4,
        overlap_chars=1,
    )

    assert pack_obj["chunks"] == [
        {
            "doc_id": pack_obj["documents"][0]["doc_id"],
            "chunk_id": f"chunk:{sha256_text('abcd')}",
            "index": 0,
            "offset_start": 0,
            "offset_end": 4,
            "text": "abcd",
            "text_sha256": sha256_text("abcd"),
        },
        {
            "doc_id": pack_obj["documents"][0]["doc_id"],
            "chunk_id": f"chunk:{sha256_text('defg')}",
            "index": 1,
            "offset_start": 3,
            "offset_end": 7,
            "text": "defg",
            "text_sha256": sha256_text("defg"),
        },
        {
            "doc_id": pack_obj["documents"][0]["doc_id"],
            "chunk_id": f"chunk:{sha256_text('ghij')}",
            "index": 2,
            "offset_start": 6,
            "offset_end": 10,
            "text": "ghij",
            "text_sha256": sha256_text("ghij"),
        },
    ]


def test_build_evidence_pack_changes_hash_when_file_changes(tmp_path: Path):
    sample_dir = tmp_path / "sample"
    sample_dir.mkdir()
    path = sample_dir / "doc.txt"
    path.write_text("one", encoding="utf-8")

    first_obj, _ = build_evidence_pack(str(sample_dir))
    path.write_text("two", encoding="utf-8")
    second_obj, _ = build_evidence_pack(str(sample_dir))

    assert first_obj["pack_sha256"] != second_obj["pack_sha256"]
