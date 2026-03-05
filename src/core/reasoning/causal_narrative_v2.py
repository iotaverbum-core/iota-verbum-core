from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.schema_validate import validate


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _line_budget(sections: list[dict], max_lines: int) -> list[dict]:
    if max_lines <= 0:
        return [{"title": section["title"], "lines": []} for section in sections]
    structural_lines = max(0, (2 * len(sections)) - 1)
    remaining = max(0, max_lines - structural_lines)
    bounded_sections = []
    for section in sections:
        lines = section["lines"][:remaining]
        bounded_sections.append({"title": section["title"], "lines": lines})
        remaining -= len(lines)
        if remaining < 0:
            remaining = 0
    return bounded_sections


def _render_text(sections: list[dict]) -> str:
    def _section_text(section: dict) -> str:
        body = "\n".join(section["lines"]) if section["lines"] else "None."
        return f"{section['title']}\n{body}"

    return "\n\n".join(_section_text(section) for section in sections) + "\n"


def render_causal_narrative_v2(
    causal_graph: dict,
    verification_result: dict | None = None,
    max_lines: int = 200,
    verbosity: str = "brief",
) -> dict:
    validate(causal_graph, "schemas/causal_graph.schema.json")
    if verification_result is not None:
        validate(verification_result, "schemas/verification_result.schema.json")

    has_cycle = any(
        finding["code"] == "CYCLE_TEMPORAL_CONSTRAINT"
        for finding in causal_graph["findings"]
    )
    summary_lines = [
        f"Nodes: {len(causal_graph['nodes'])}",
        f"Edges: {len(causal_graph['edges'])}",
        f"Temporal cycle: {'yes' if has_cycle else 'no'}",
    ]
    if verification_result is not None:
        summary_lines.append(f"Verification: {verification_result['status']}")

    order_limit = 10 if verbosity == "brief" else max(10, len(causal_graph["nodes"]))
    order_lines = [
        f"- {event_id}"
        for event_id in causal_graph["causal_order"][:order_limit]
    ]

    edge_limit = 8 if verbosity == "brief" else len(causal_graph["edges"])
    edge_lines = []
    for edge in causal_graph["edges"][:edge_limit]:
        line = (
            f"- {edge['from_event_id']} -> {edge['to_event_id']} "
            f"[{edge['type']}, {edge['reason_code']}, {edge['confidence']}]"
        )
        if verbosity == "full":
            line += f" evidence={len(edge['evidence'])}"
        edge_lines.append(line)

    finding_limit = 8 if verbosity == "brief" else len(causal_graph["findings"])
    finding_lines = []
    for finding in causal_graph["findings"][:finding_limit]:
        line = (
            f"- {finding['code']}: "
            + ", ".join(finding["event_ids"])
        )
        if verbosity == "full" and "details" in finding:
            line += f" details={_sort_key(finding['details'])}"
        finding_lines.append(line)

    sections = [
        {"title": "Summary", "lines": summary_lines},
        {"title": "Causal Order", "lines": order_lines},
        {"title": "Edges", "lines": edge_lines},
        {"title": "Findings", "lines": finding_lines},
    ]
    bounded_sections = _line_budget(sections, max_lines)
    narrative = {
        "narrative_version": "2.0",
        "mode": verbosity,
        "text": _render_text(bounded_sections),
        "sections": bounded_sections,
        "graph_summary": {
            "node_count": len(causal_graph["nodes"]),
            "edge_count": len(causal_graph["edges"]),
            "finding_count": len(causal_graph["findings"]),
            "has_temporal_cycle": has_cycle,
            "first_causal_order": causal_graph["causal_order"][:10],
        },
    }
    validate(narrative, "schemas/causal_narrative_v2.schema.json")
    return narrative
