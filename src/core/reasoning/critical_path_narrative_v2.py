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


def render_critical_path_narrative_v2(
    critical_path: dict,
    *,
    mode: str = "brief",
    max_lines: int = 200,
) -> dict:
    validate(critical_path, "schemas/critical_path.schema.json")

    top_event = critical_path["top_events"][0] if critical_path["top_events"] else None
    summary_lines = [
        f"Top events: {len(critical_path['top_events'])}",
        f"Critical chain length: {len(critical_path['critical_chain'])}",
        (
            "Cycle detected: yes"
            if critical_path["receipts"].get("cycle_detected", False)
            else "Cycle detected: no"
        ),
    ]
    if top_event is not None:
        summary_lines.append(
            f"Top event: {top_event['event_id']} score={top_event['score']}"
        )

    top_limit = 5 if mode == "brief" else len(critical_path["top_events"])
    top_lines = [
        (
            f"- {item['event_id']} score={item['score']} "
            f"fan_out={item['fan_out']} reach={item['downstream_reach']}"
        )
        for item in critical_path["top_events"][:top_limit]
    ]
    chain_lines = [f"- {event_id}" for event_id in critical_path["critical_chain"]]
    receipt_lines = [
        "Edge types: " + ", ".join(critical_path["receipts"]["edge_types_used"]),
        f"Nodes: {critical_path['receipts']['counts']['nodes']}",
        f"Edges: {critical_path['receipts']['counts']['edges']}",
    ]
    sections = [
        {"title": "Summary", "lines": summary_lines},
        {"title": "Top Events", "lines": top_lines},
        {"title": "Critical Chain", "lines": chain_lines},
        {"title": "Receipts", "lines": receipt_lines},
    ]
    bounded = _line_budget(sections, max_lines)
    narrative = {
        "narrative_version": "2.0",
        "mode": mode,
        "text": _render_text(bounded),
        "sections": bounded,
        "summary": {
            "top_event_id": top_event["event_id"] if top_event is not None else "",
            "top_score": top_event["score"] if top_event is not None else 0,
            "chain_length": len(critical_path["critical_chain"]),
            "cycle_detected": critical_path["receipts"].get(
                "cycle_detected",
                False,
            ),
        },
    }
    validate(narrative, "schemas/critical_path_narrative_v2.schema.json")
    return narrative
