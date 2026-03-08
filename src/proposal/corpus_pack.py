from __future__ import annotations

from pathlib import Path
from typing import Iterator

from core.determinism.hashing import sha256_text
from proposal.text_normalize import normalize_text


def iter_source_files(folder: Path) -> Iterator[Path]:
    files = [
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}
    ]
    for path in sorted(files, key=lambda item: item.relative_to(folder).as_posix()):
        yield path


def count_words(text: str) -> int:
    return len([token for token in normalize_text(text).split(" ") if token])


def build_document_manifest_item(*, root: Path, path: Path, text: str) -> dict:
    normalized = normalize_text(text)
    text_bytes = normalized.encode("utf-8")
    relpath = path.relative_to(root).as_posix()
    sha = sha256_text(normalized)
    doc_id = f"doc:{sha}"
    return {
        "doc_id": doc_id,
        "relative_path": relpath,
        "relpath": relpath,
        "content_sha256": sha,
        "sha256": sha,
        "byte_count": len(text_bytes),
        "bytes": len(text_bytes),
        "char_count": len(normalized),
        "word_count": count_words(normalized),
    }
