from __future__ import annotations

import re
from dataclasses import dataclass

from core.determinism.hashing import sha256_text
from proposal.category_rules import infer_categories
from proposal.text_normalize import normalize_text

_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)[\).\s]+([A-Z][^\n]{1,120})$")
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


@dataclass(frozen=True)
class Heading:
    line_index: int
    level: int
    text: str


def _is_underlined_heading(lines: list[str], index: int) -> tuple[bool, int]:
    if index + 1 >= len(lines):
        return False, 0
    title_line = lines[index].strip()
    underline = lines[index + 1].strip()
    if not title_line or len(title_line) > 120:
        return False, 0
    if re.fullmatch(r"=+", underline):
        return True, 1
    if re.fullmatch(r"-+", underline):
        return True, 2
    return False, 0


def _extract_title(lines: list[str]) -> str:
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        md_match = _MD_HEADING_RE.match(stripped)
        if md_match and md_match.group(1) == "#":
            return normalize_text(md_match.group(2))
        underlined, _ = _is_underlined_heading(lines, i)
        if underlined:
            return normalize_text(stripped)
        return normalize_text(stripped[:140])
    return "Untitled"


def _extract_headings(lines: list[str]) -> list[Heading]:
    headings: list[Heading] = []
    skip_indices: set[int] = set()
    for i, line in enumerate(lines):
        if i in skip_indices:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        md_match = _MD_HEADING_RE.match(stripped)
        if md_match:
            headings.append(Heading(i, len(md_match.group(1)), normalize_text(md_match.group(2))))
            continue
        underlined, level = _is_underlined_heading(lines, i)
        if underlined:
            headings.append(Heading(i, level, normalize_text(stripped)))
            skip_indices.add(i + 1)
            continue
        numbered_match = _NUMBERED_HEADING_RE.match(stripped)
        if numbered_match:
            depth = len(numbered_match.group(1).split("."))
            headings.append(Heading(i, min(6, depth + 1), normalize_text(numbered_match.group(2))))
    return headings


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def extract_document_structure(*, doc_id: str, relative_path: str, text: str) -> dict:
    normalized = normalize_text(text)
    lines = normalized.split("\n")
    title = _extract_title(lines)
    headings = _extract_headings(lines)
    heading_summary = [f"{'#' * heading.level} {heading.text}" for heading in headings]

    if not headings:
        headings = [Heading(0, 1, title)]

    sections: list[dict] = []
    heading_stack: list[str] = []
    line_starts: list[int] = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1

    for idx, heading in enumerate(headings):
        while len(heading_stack) >= heading.level:
            heading_stack.pop()
        heading_stack.append(heading.text)
        start_line = heading.line_index
        end_line = headings[idx + 1].line_index if idx + 1 < len(headings) else len(lines)
        content = "\n".join(lines[start_line:end_line]).strip("\n")
        start_offset = line_starts[start_line] if start_line < len(line_starts) else 0
        if end_line < len(line_starts):
            end_offset = line_starts[end_line]
        else:
            end_offset = len(normalized)
        section_path = heading_stack.copy()
        section_key = f"{doc_id}|{'/'.join(section_path)}|{start_offset}|{end_offset}"
        section_id = "section:" + sha256_text(section_key)
        words = _WORD_RE.findall(content.lower())
        keyword_counts = sorted(
            ((word, words.count(word)) for word in sorted(set(words)) if len(word) >= 4),
            key=lambda item: (-item[1], item[0]),
        )
        context_keywords = [word for word, _ in keyword_counts[:8]]
        sections.append(
            {
                "section_id": section_id,
                "heading": heading.text,
                "heading_level": heading.level,
                "heading_path": section_path,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "word_count": _word_count(content),
                "char_count": len(content),
                "context_keywords": context_keywords,
                "content_sha256": sha256_text(content),
            }
        )

    category_result = infer_categories(
        title=title,
        headings=[heading.text for heading in headings],
        content=normalized,
    )
    return {
        "doc_id": doc_id,
        "relative_path": relative_path,
        "title": title,
        "headings": heading_summary,
        "sections": sections,
        "categories": category_result["categories"],
        "category_receipts": category_result["category_receipts"],
    }
