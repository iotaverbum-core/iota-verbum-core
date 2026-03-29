from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate
from proposal.chunking import chunk_document
from proposal.corpus_pack import (
    build_document_manifest_item,
    count_words,
    iter_source_files,
)
from proposal.section_chunker import chunk_document_by_sections
from proposal.structure_extract import extract_document_structure
from proposal.text_normalize import normalize_text


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
    max_docs: int = 100,
    max_total_words: int = 500_000,
    max_total_chunks: int = 2_000,
    chunk_target_words: int = 450,
    chunk_overlap_words: int = 75,
    extract_structure: bool = False,
    categorize: bool = False,
) -> tuple[dict, bytes]:
    root = Path(folder)
    documents = []
    chunks = []
    corpus_documents = []
    corpus_structures = []

    total_words = 0
    global_chunk_index = 0
    for index, path in enumerate(iter_source_files(root)):
        if index >= max_docs:
            break
        raw_bytes = path.read_bytes()
        relpath = path.relative_to(root).as_posix()
        try:
            decoded_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"file is not valid UTF-8: {relpath}") from exc

        canonical_doc_text = normalize_text(decoded_text)
        doc_item = build_document_manifest_item(
            root=root,
            path=path,
            text=canonical_doc_text,
        )
        if total_words + doc_item["word_count"] > max_total_words:
            break
        total_words += doc_item["word_count"]

        structure = extract_document_structure(
            doc_id=doc_item["doc_id"],
            relative_path=doc_item["relative_path"],
            text=canonical_doc_text,
        )
        doc_item["title"] = structure["title"]
        doc_item["detected_categories"] = structure["categories"] if categorize else []
        doc_item["detected_headings_summary"] = structure["headings"]
        documents.append(doc_item)
        corpus_documents.append(
            {
                "doc_id": doc_item["doc_id"],
                "relative_path": doc_item["relative_path"],
                "content_sha256": doc_item["content_sha256"],
                "byte_count": doc_item["byte_count"],
                "char_count": doc_item["char_count"],
                "word_count": doc_item["word_count"],
                "title": structure["title"],
                "detected_categories": doc_item["detected_categories"],
                "detected_headings_summary": structure["headings"],
            }
        )

        if extract_structure:
            corpus_structures.append(structure)
            doc_chunks = chunk_document_by_sections(
                doc_id=doc_item["doc_id"],
                relative_path=doc_item["relative_path"],
                title=structure["title"],
                categories=structure["categories"] if categorize else [],
                sections=structure["sections"],
                text=canonical_doc_text,
                chunk_target_words=chunk_target_words,
                chunk_overlap_words=chunk_overlap_words,
                global_chunk_start=global_chunk_index,
            )
        else:
            doc_chunks = []
            for chunk in chunk_document(
                canonical_doc_text,
                max_chars=max_chars,
                overlap_chars=overlap_chars,
            ):
                doc_chunks.append(
                    {
                        "doc_id": doc_item["doc_id"],
                        "chunk_id": f"chunk:{chunk['text_sha256']}",
                        "index": chunk["index"],
                        "chunk_index_in_doc": chunk["index"],
                        "global_chunk_index": global_chunk_index + chunk["index"],
                        "offset_start": chunk["offset_start"],
                        "offset_end": chunk["offset_end"],
                        "text": chunk["text"],
                        "text_sha256": chunk["text_sha256"],
                        "section_id": "",
                        "heading_path": [],
                        "title": structure["title"],
                        "categories": structure["categories"] if categorize else [],
                        "relative_path": doc_item["relative_path"],
                        "word_count": count_words(chunk["text"]),
                        "char_count": len(chunk["text"]),
                        "neighbor_section_ids": ["", ""],
                        "section_context_keywords": [],
                    }
                )

        available = max_total_chunks - len(chunks)
        if available <= 0:
            break
        selected_doc_chunks = doc_chunks[:available]
        chunks.extend(selected_doc_chunks)
        global_chunk_index += len(selected_doc_chunks)
        if len(chunks) >= max_total_chunks:
            break

    pack_obj = {
        "pack_version": "1.1",
        "root_hint": root_hint,
        "limits": {
            "max_docs": max_docs,
            "max_total_words": max_total_words,
            "max_total_chunks": max_total_chunks,
            "chunk_target_words": chunk_target_words,
            "chunk_overlap_words": chunk_overlap_words,
        },
        "corpus_manifest": {
            "total_docs": len(corpus_documents),
            "total_words": sum(item["word_count"] for item in corpus_documents),
            "documents": corpus_documents,
        },
        "document_structure": corpus_structures,
        "documents": documents,
        "chunks": chunks,
        "pack_sha256": "",
    }
    pack_obj["pack_sha256"] = _compute_pack_sha256(pack_obj)
    validate(pack_obj, "schemas/evidence_pack.schema.json")
    pack_bytes = dumps_canonical(pack_obj)
    return pack_obj, pack_bytes
