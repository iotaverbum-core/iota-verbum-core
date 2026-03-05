from __future__ import annotations


def chunk_document(
    text: str,
    *,
    max_chars: int = 1200,
    overlap_chars: int = 120,
) -> list[dict]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be non-negative")
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be smaller than max_chars")
    if not text:
        return []

    chunks = []
    start = 0
    index = 0
    step = max_chars - overlap_chars
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk_text = text[start:end]
        if chunk_text:
            chunks.append(
                {
                    "index": index,
                    "offset_start": start,
                    "offset_end": end,
                    "text": chunk_text,
                }
            )
            index += 1
        if end >= len(text):
            break
        start += step

    return chunks
