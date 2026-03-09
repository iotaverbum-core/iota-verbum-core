from __future__ import annotations


def render_world_diff_markdown(diff: dict) -> str:
    report = diff["diff_report"]
    return (
        "# World Diff\n"
        f"- New entities: {', '.join(report['newly_introduced_entities']) or 'none'}\n"
        f"- New events: {', '.join(report['newly_introduced_events']) or 'none'}\n"
        f"- Resolved unknowns: {', '.join(report['resolved_unknowns']) or 'none'}\n"
    )
