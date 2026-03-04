from __future__ import annotations

from core.determinism.schema_validate import validate


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


def render_counterfactual_narrative_v2(
    *,
    task: dict,
    result: dict,
    world_diff_narrative: dict,
    base_output: dict,
    counterfactual_output: dict,
) -> dict:
    validate(task, "schemas/counterfactual_task.schema.json")
    validate(result, "schemas/counterfactual_result.schema.json")
    validate(world_diff_narrative, "schemas/world_diff_narrative.schema.json")

    base_causal = base_output["causal_graph"]
    new_causal = counterfactual_output["causal_graph"]
    has_cycle_old = any(
        finding["code"] == "CYCLE_TEMPORAL_CONSTRAINT"
        for finding in base_causal["findings"]
    )
    has_cycle_new = any(
        finding["code"] == "CYCLE_TEMPORAL_CONSTRAINT"
        for finding in new_causal["findings"]
    )
    mode = task["options"]["mode"]
    max_lines = task["options"]["max_lines"]
    order_limit = 5 if mode == "brief" else 10
    changed_event_limit = (
        8 if mode == "brief" else len(result["effects"]["changed_events"])
    )

    sections = [
        {
            "title": "Operation",
            "lines": [
                f"Task: {task['task_id']}",
                f"Type: {task['operation']['type']}",
                f"Target: {task['operation']['target_id']}",
            ],
        },
        {
            "title": "What changed",
            "lines": [
                "Removed events: "
                + (", ".join(result["effects"]["removed"]["events"]) or "none"),
                "Removed entities: "
                + (", ".join(result["effects"]["removed"]["entities"]) or "none"),
                *[
                    f"- {item['event_id']}: {', '.join(item['fields_changed'])}"
                    for item in result["effects"]["changed_events"][
                        :changed_event_limit
                    ]
                ],
            ],
        },
        {
            "title": "Verification change",
            "lines": [
                f"{result['effects']['verification_change']['old']} -> "
                f"{result['effects']['verification_change']['new']}",
                "Unknowns: "
                f"{result['effects']['changed_unknowns_count']['old']} -> "
                f"{result['effects']['changed_unknowns_count']['new']}",
            ],
        },
        {
            "title": "Causal change summary",
            "lines": [
                f"Edges: {len(base_causal['edges'])} -> {len(new_causal['edges'])}",
                f"Cycle: {'yes' if has_cycle_old else 'no'} -> "
                f"{'yes' if has_cycle_new else 'no'}",
                "Order: "
                + (
                    ", ".join(new_causal["causal_order"][:order_limit])
                    if new_causal["causal_order"]
                    else "none"
                ),
            ],
        },
        {
            "title": "World diff",
            "lines": world_diff_narrative["sections"][0]["lines"]
            + world_diff_narrative["sections"][1]["lines"][:3],
        },
        {
            "title": "Receipts",
            "lines": [
                f"Base output: {result['base_hashes']['output_sha256']}",
                "Counterfactual output: "
                f"{result['counterfactual_hashes']['output_sha256']}",
                f"Base path: {result['receipts']['base_path']}",
                f"Counterfactual path: {result['receipts']['counterfactual_path']}",
            ],
        },
    ]
    bounded_sections = _line_budget(sections, max_lines)
    narrative = {
        "narrative_version": "2.0",
        "mode": mode,
        "text": _render_text(bounded_sections),
        "sections": bounded_sections,
        "summary": {
            "task_id": task["task_id"],
            "verification_old": result["effects"]["verification_change"]["old"],
            "verification_new": result["effects"]["verification_change"]["new"],
            "causal_edges_old": len(base_causal["edges"]),
            "causal_edges_new": len(new_causal["edges"]),
            "has_cycle_old": has_cycle_old,
            "has_cycle_new": has_cycle_new,
        },
    }
    validate(narrative, "schemas/counterfactual_narrative_v2.schema.json")
    return narrative
