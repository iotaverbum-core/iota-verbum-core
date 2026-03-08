from __future__ import annotations

import re

from core.determinism.hashing import sha256_text
from proposal.text_normalize import normalize_text

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _split_paragraphs(text: str) -> list[str]:
    normalized = normalize_text(text)
    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    return paragraphs or ([normalized] if normalized else [])


def chunk_document_by_sections(
    *,
    doc_id: str,
    relative_path: str,
    title: str,
    categories: list[str],
    sections: list[dict],
    text: str,
    chunk_target_words: int,
    chunk_overlap_words: int,
    global_chunk_start: int,
) -> list[dict]:
    if chunk_target_words <= 0:
        raise ValueError("chunk_target_words must be positive")
    if chunk_overlap_words < 0 or chunk_overlap_words >= chunk_target_words:
        raise ValueError("chunk_overlap_words must be >=0 and < chunk_target_words")

    chunks: list[dict] = []
    chunk_index_in_doc = 0
    global_index = global_chunk_start
    for section_index, section in enumerate(sections):
        section_text = normalize_text(
            text[section["start_offset"] : section["end_offset"]]
        ).strip()
        paragraphs = _split_paragraphs(section_text)
        current: list[str] = []
        current_words = 0
        overlap_buffer: list[str] = []

        def flush_chunk() -> None:
            nonlocal current
            nonlocal current_words
            nonlocal overlap_buffer
            nonlocal chunk_index_in_doc
            nonlocal global_index
            if not current:
                return
            chunk_text = "\n\n".join(current).strip()
            if not chunk_text:
                return
            chunk_sha = sha256_text(chunk_text)
            chunks.append(
                {
                    "doc_id": doc_id,
                    "section_id": section["section_id"],
                    "chunk_id": f"chunk:{chunk_sha}",
                    "index": chunk_index_in_doc,
                    "chunk_index_in_doc": chunk_index_in_doc,
                    "global_chunk_index": global_index,
                    "offset_start": section["start_offset"],
                    "offset_end": section["end_offset"],
                    "text": chunk_text,
                    "text_sha256": chunk_sha,
                    "heading_path": section["heading_path"],
                    "title": title,
                    "categories": categories,
                    "relative_path": relative_path,
                    "word_count": _word_count(chunk_text),
                    "char_count": len(chunk_text),
                    "neighbor_section_ids": [
                        (
                            sections[section_index - 1]["section_id"]
                            if section_index > 0
                            else ""
                        ),
                        (
                            sections[section_index + 1]["section_id"]
                            if section_index + 1 < len(sections)
                            else ""
                        ),
                    ],
                    "section_context_keywords": section["context_keywords"],
                }
            )
            chunk_index_in_doc += 1
            global_index += 1
            tokens = chunk_text.split()
            overlap_buffer = (
                tokens[-chunk_overlap_words:] if chunk_overlap_words else []
            )
            if overlap_buffer:
                current = [" ".join(overlap_buffer)]
                current_words = len(overlap_buffer)
            else:
                current = []
                current_words = 0

        for paragraph in paragraphs:
            paragraph_words = _word_count(paragraph)
            if paragraph_words == 0:
                continue
            if current_words + paragraph_words > chunk_target_words and current:
                flush_chunk()
            if paragraph_words > chunk_target_words:
                words = paragraph.split()
                start = 0
                step = chunk_target_words - chunk_overlap_words
                while start < len(words):
                    end = min(start + chunk_target_words, len(words))
                    slice_text = " ".join(words[start:end])
                    current = [slice_text]
                    current_words = _word_count(slice_text)
                    flush_chunk()
                    if end >= len(words):
                        break
                    start += step
            else:
                current.append(paragraph)
                current_words += paragraph_words

        flush_chunk()

    return chunks
