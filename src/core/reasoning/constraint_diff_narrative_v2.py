from __future__ import annotations

from core.determinism.schema_validate import validate


def _line_budget(sections: list[dict], max_lines: int) -> list[dict]:
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


def _changed_line(item: dict) -> str:
    return (
        f"- {item['new']['type']}: "
        f"{item['old']['reason']} -> {item['new']['reason']}"
    )


def render_constraint_diff_narrative_v2(
    diff: dict,
    *,
    mode: str = "brief",
    max_lines: int = 200,
) -> dict:
    validate(diff, "schemas/constraint_diff.schema.json")
    summary_lines = [
        (
            "Delta: "
            f"Violations {diff['counts']['old_total']}->{diff['counts']['new_total']}, "
            f"Added {diff['counts']['added']}, "
            f"Removed {diff['counts']['removed']}, "
            f"Changed {diff['counts']['changed']}, "
            f"Verification {diff['verification_change']['old']}->"
            f"{diff['verification_change']['new']}"
        )
    ]
    added_lines = [
        f"- {item['type']}: {item['reason']}"
        for item in diff["violations"]["added"][:10]
    ]
    removed_lines = [
        f"- {item['type']}: {item['reason']}"
        for item in diff["violations"]["removed"][:10]
    ]
    if mode == "full":
        changed_lines = [
            _changed_line(item)
            for item in diff["violations"]["changed"][: max_lines]
        ]
    else:
        changed_lines = [
            _changed_line(item) for item in diff["violations"]["changed"][:10]
        ]
    receipt_lines = [
        f"Old output_sha256: {diff['old']['output_sha256']}",
        f"New output_sha256: {diff['new']['output_sha256']}",
        f"Old world_sha256: {diff['old']['world_sha256']}",
        f"New world_sha256: {diff['new']['world_sha256']}",
    ]
    sections = [
        {"title": "Summary", "lines": summary_lines},
        {"title": "Added violations", "lines": added_lines},
        {"title": "Removed violations", "lines": removed_lines},
        {"title": "Changed violations", "lines": changed_lines},
        {"title": "Receipts", "lines": receipt_lines},
    ]
    bounded = _line_budget(sections, max_lines)
    narrative = {
        "narrative_version": "2.0",
        "mode": mode,
        "text": _render_text(bounded),
        "sections": bounded,
        "summary": {
            "old_total": diff["counts"]["old_total"],
            "new_total": diff["counts"]["new_total"],
            "added": diff["counts"]["added"],
            "removed": diff["counts"]["removed"],
            "changed": diff["counts"]["changed"],
            "verification_old": diff["verification_change"]["old"],
            "verification_new": diff["verification_change"]["new"],
        },
    }
    validate(narrative, "schemas/constraint_diff_narrative_v2.schema.json")
    return narrative
