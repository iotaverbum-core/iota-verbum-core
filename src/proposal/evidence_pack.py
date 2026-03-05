from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes, sha256_text
from core.determinism.schema_validate import validate
from proposal.chunking import chunk_document
from proposal.text_normalize import normalize_text


def _iter_source_files(folder: Path) -> list[Path]:
    files = [
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}
    ]
    return sorted(
        files,
        key=lambda path: path.relative_to(folder).as_posix(),
    )


def _compute_pack_sha256(pack_obj: dict) -> str:
    pack_for_hash = deepcopy(pack_obj)
    pack_for_hash["pack_sha256"] = ""
    canonical_bytes = dumps_canonical(pack_for_hash)
    return sha256_bytes(canonical_bytes)


def build_evidence_pack(
    folder: str,
    *,
    root_hint: str = "",
    max_chars: int = 1200,
    overlap_chars: int = 120,
) -> tuple[dict, bytes]:
    root = Path(folder)
    documents = []
    chunks = []

    for path in _iter_source_files(root):
        relpath = path.relative_to(root).as_posix()
        raw_bytes = path.read_bytes()
        try:
            decoded_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"file is not valid UTF-8: {relpath}") from exc

        canonical_doc_text = normalize_text(decoded_text)
        doc_sha256 = sha256_text(canonical_doc_text)
        doc_id = f"doc:{doc_sha256}"
        canonical_doc_bytes = canonical_doc_text.encode("utf-8")

        documents.append(
            {
                "doc_id": doc_id,
                "relpath": relpath,
                "sha256": doc_sha256,
                "bytes": len(canonical_doc_bytes),
            }
        )

        for chunk in chunk_document(
            canonical_doc_text,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        ):
            chunk_sha256 = sha256_text(chunk["text"])
            chunks.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": f"chunk:{chunk_sha256}",
                    "index": chunk["index"],
                    "offset_start": chunk["offset_start"],
                    "offset_end": chunk["offset_end"],
                    "text": chunk["text"],
                    "text_sha256": chunk_sha256,
                }
            )

    pack_obj = {
        "pack_version": "1.0",
        "root_hint": root_hint,
        "documents": documents,
        "chunks": chunks,
        "pack_sha256": "",
    }
    pack_obj["pack_sha256"] = _compute_pack_sha256(pack_obj)
    validate(pack_obj, "schemas/evidence_pack.schema.json")
    pack_bytes = dumps_canonical(pack_obj)
    return pack_obj, pack_bytes
