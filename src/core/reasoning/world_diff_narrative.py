from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical
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

    return (
        "\n\n".join(_section_text(section) for section in sections)
        + "\n"
    )


def _compact(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def render_world_diff_narrative(
    diff: dict,
    mode: str = "brief",
    max_lines: int = 200,
) -> dict:
    validate(diff, "schemas/world_diff.schema.json")
    delta_line = (
        "Delta: "
        f"Entities +{len(diff['entities']['added'])}"
        f"/-{len(diff['entities']['removed'])}, "
        f"Events +{len(diff['events']['added'])}"
        f"/-{len(diff['events']['removed'])}, "
        f"Changed {len(diff['events']['changed'])}, "
        f"Unknowns +{len(diff['unknowns']['added'])}"
        f"/-{len(diff['unknowns']['removed'])}, "
        f"Conflicts +{len(diff['conflicts']['added'])}"
        f"/-{len(diff['conflicts']['removed'])}, "
        "Verification "
        f"{diff['verification']['old_status']}"
        f"->{diff['verification']['new_status']}"
    )
    summary_lines = [delta_line]
    whats_new = [
        *(
            f"- entity added: {entity_id}"
            for entity_id in diff["entities"]["added"][:10]
        ),
        *(f"- event added: {event_id}" for event_id in diff["events"]["added"][:10]),
    ]
    changed_lines = []
    for item in diff["events"]["changed"][:10]:
        fields = ",".join(change["field"] for change in item["changes"])
        changed_lines.append(f"- {item['event_id']}: {fields}")
    resolved_lines = [
        *(
            f"- unknown removed: {_compact(item)}"
            for item in diff["unknowns"]["removed"][:10]
        ),
        *(
            f"- conflict removed: {item['kind']}: {item['reason']}"
            for item in diff["conflicts"]["removed"][:10]
        ),
    ]
    attention_lines = [
        *(
            f"- unknown added: {_compact(item)}"
            for item in diff["unknowns"]["added"][:10]
        ),
        *(
            f"- conflict added: {item['kind']}: {item['reason']}"
            for item in diff["conflicts"]["added"][:10]
        ),
        *(
            f"- required info added: {_compact(item)}"
            for item in diff["verification"]["required_info_added"][:10]
        ),
    ]
    if mode == "full":
        changed_lines = [
            "- " + _compact(item)
            for item in diff["events"]["changed"][: max(0, max_lines)]
        ]
    sections = [
        {"title": "Summary", "lines": summary_lines},
        {"title": "What's new", "lines": whats_new},
        {"title": "What changed", "lines": changed_lines},
        {"title": "What got resolved", "lines": resolved_lines},
        {"title": "What needs attention", "lines": attention_lines},
    ]
    bounded_sections = _line_budget(sections, max_lines)
    narrative = {
        "world_diff_narrative_version": "1.0",
        "mode": mode,
        "text": _render_text(bounded_sections),
        "sections": bounded_sections,
    }
    validate(narrative, "schemas/world_diff_narrative.schema.json")
    return narrative
