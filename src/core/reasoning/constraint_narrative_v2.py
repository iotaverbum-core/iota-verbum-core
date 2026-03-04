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


def render_constraint_narrative_v2(
    constraint_report: dict,
    *,
    mode: str = "brief",
    max_lines: int = 200,
) -> dict:
    validate(constraint_report, "schemas/constraint_report.schema.json")
    violations = constraint_report["violations"]
    summary_lines = [
        f"Violations: {len(violations)}",
        f"Policy: {constraint_report['counts']['policy']}",
        f"Temporal: {constraint_report['counts']['temporal']}",
        f"Causal: {constraint_report['counts']['causal']}",
        f"State: {constraint_report['counts']['state']}",
    ]
    violation_limit = 8 if mode == "brief" else len(violations)
    violation_lines = [
        f"- {item['type']}: {item['reason']}"
        for item in violations[:violation_limit]
    ]
    affected_events = sorted(
        {
            event_id
            for item in violations
            for event_id in item["events"]
        }
    )
    event_lines = [f"- {event_id}" for event_id in affected_events[:violation_limit]]
    receipt_lines = [
        f"Total evidence refs: {sum(len(item['evidence']) for item in violations)}",
        "First evidence counts: "
        + (
            ", ".join(str(len(item["evidence"])) for item in violations[:5])
            or "none"
        ),
    ]
    sections = [
        {"title": "Constraint Summary", "lines": summary_lines},
        {"title": "Violations", "lines": violation_lines},
        {"title": "Affected events", "lines": event_lines},
        {"title": "Receipts", "lines": receipt_lines},
    ]
    bounded = _line_budget(sections, max_lines)
    narrative = {
        "narrative_version": "2.0",
        "mode": mode,
        "text": _render_text(bounded),
        "sections": bounded,
        "summary": {
            "violation_count": len(violations),
            "policy_count": constraint_report["counts"]["policy"],
            "temporal_count": constraint_report["counts"]["temporal"],
            "causal_count": constraint_report["counts"]["causal"],
            "state_count": constraint_report["counts"]["state"],
        },
    }
    validate(narrative, "schemas/constraint_narrative_v2.schema.json")
    return narrative
