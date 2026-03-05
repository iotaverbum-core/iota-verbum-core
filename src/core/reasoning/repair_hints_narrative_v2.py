from __future__ import annotations

from core.determinism.schema_validate import validate


def _line_budget(sections: list[dict], max_lines: int) -> list[dict]:
    if max_lines <= 0:
        return [{"title": section["title"], "lines": []} for section in sections]
    structural_lines = max(0, (2 * len(sections)) - 1)
    remaining = max(0, max_lines - structural_lines)
    bounded = []
    for section in sections:
        lines = section["lines"][:remaining]
        bounded.append({"title": section["title"], "lines": lines})
        remaining -= len(lines)
        if remaining < 0:
            remaining = 0
    return bounded


def _render_text(sections: list[dict]) -> str:
    def _section_text(section: dict) -> str:
        body = "\n".join(section["lines"]) if section["lines"] else "None."
        return f"{section['title']}\n{body}"

    return "\n\n".join(_section_text(section) for section in sections) + "\n"


def render_repair_hints_narrative_v2(
    repair_hints: dict,
    *,
    max_lines: int = 200,
    verbosity: str = "brief",
) -> dict:
    validate(repair_hints, "schemas/repair_hints.schema.json")
    hints = repair_hints["hints"]
    hint_limit = 6 if verbosity == "brief" else len(hints)
    summary_lines = [
        f"Hints: {len(hints)}",
        f"Low risk: {sum(1 for hint in hints if hint['risk'] == 'low')}",
        f"Medium risk: {sum(1 for hint in hints if hint['risk'] == 'medium')}",
        f"High risk: {sum(1 for hint in hints if hint['risk'] == 'high')}",
    ]
    hint_targets = [
        ", ".join(hint["target"]["event_ids"] + hint["target"]["entity_ids"]) or "none"
        for hint in hints[:hint_limit]
    ]
    hint_lines = [
        f"- {hint['action']} on {target}"
        for hint, target in zip(hints[:hint_limit], hint_targets, strict=True)
    ]
    rationale_lines = [
        f"- {hint['hint_id']}: {hint['rationale']}"
        for hint in hints[:hint_limit]
    ]
    total_violation_receipts = sum(
        len(hint["receipts"]["violation_receipts"])
        for hint in hints
    )
    total_related_edges = sum(
        len(hint["receipts"]["related_edges"])
        for hint in hints
    )
    receipt_lines = [
        f"Total violation receipts: {total_violation_receipts}",
        f"Total related edges: {total_related_edges}",
    ]
    sections = [
        {"title": "Repair Hint Summary", "lines": summary_lines},
        {"title": "Hints", "lines": hint_lines},
        {"title": "Rationales", "lines": rationale_lines},
        {"title": "Receipts", "lines": receipt_lines},
    ]
    bounded = _line_budget(sections, max_lines)
    narrative = {
        "narrative_version": "2.0",
        "verbosity": verbosity,
        "text": _render_text(bounded),
        "sections": bounded,
        "summary": {
            "hint_count": len(hints),
            "low_risk_count": sum(1 for hint in hints if hint["risk"] == "low"),
            "medium_risk_count": sum(
                1 for hint in hints if hint["risk"] == "medium"
            ),
            "high_risk_count": sum(1 for hint in hints if hint["risk"] == "high"),
        },
    }
    validate(narrative, "schemas/repair_hints_narrative_v2.schema.json")
    return narrative
