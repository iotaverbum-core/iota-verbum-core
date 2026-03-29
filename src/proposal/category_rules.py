from __future__ import annotations

import re
from collections import defaultdict

from proposal.text_normalize import normalize_text

TAXONOMY: tuple[str, ...] = (
    "correspondence",
    "evidence",
    "finance",
    "incident",
    "legal",
    "meeting-notes",
    "operations",
    "policy",
    "requirements",
    "technical",
    "timeline",
)

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "policy": ("policy", "standard", "governance", "control"),
    "incident": ("incident", "breach", "outage", "postmortem"),
    "legal": ("agreement", "contract", "clause", "indemnity", "law"),
    "finance": ("invoice", "budget", "payment", "revenue", "expense"),
    "operations": ("runbook", "operation", "deployment", "on-call", "sla"),
    "technical": ("architecture", "api", "database", "system", "service"),
    "correspondence": ("from:", "to:", "subject:", "regards", "sincerely"),
    "meeting-notes": ("agenda", "minutes", "attendees", "action items"),
    "requirements": ("requirement", "must", "shall", "acceptance criteria"),
    "timeline": ("timeline", "date", "milestone", "phase", "chronology"),
    "evidence": ("evidence", "exhibit", "attachment", "log", "receipt"),
}

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def _word_tokens(text: str) -> list[str]:
    normalized = normalize_text(text).lower()
    return [token for token in _WORD_RE.findall(normalized) if token]


def infer_categories(*, title: str, headings: list[str], content: str) -> dict:
    joined_headings = "\n".join(headings)
    combined = "\n".join((title, joined_headings, content))
    tokens = _word_tokens(combined)
    normalized_text = " ".join(tokens)

    scores: dict[str, int] = defaultdict(int)
    receipts: list[dict] = []
    for category in TAXONOMY:
        for keyword in _CATEGORY_KEYWORDS[category]:
            normalized_keyword = normalize_text(keyword).lower()
            if " " in normalized_keyword or ":" in normalized_keyword:
                count = normalize_text(combined).lower().count(normalized_keyword)
            else:
                count = normalized_text.count(normalized_keyword)
            if count <= 0:
                continue
            score = count * (
                3
                if any(
                    normalized_keyword in normalize_text(heading).lower()
                    for heading in headings
                )
                else 1
            )
            scores[category] += score
            receipts.append(
                {
                    "category": category,
                    "reason": f"matched keyword '{keyword}'",
                    "evidence_ref": f"keyword:{normalized_keyword}",
                    "score": score,
                }
            )

    ordered = sorted(
        ((category, score) for category, score in scores.items() if score > 0),
        key=lambda item: (-item[1], item[0]),
    )
    categories = [category for category, _ in ordered]
    if not categories:
        categories = ["technical"]
        receipts.append(
            {
                "category": "technical",
                "reason": "default fallback category",
                "evidence_ref": "fallback:taxonomy-default",
                "score": 0,
            }
        )

    sorted_receipts = sorted(
        receipts,
        key=lambda item: (
            item["category"],
            item["evidence_ref"],
            item["reason"],
            -item["score"],
        ),
    )
    for item in sorted_receipts:
        del item["score"]
    return {"categories": categories, "category_receipts": sorted_receipts}
