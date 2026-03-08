from __future__ import annotations


def render_narrative_outputs(
    narrative: dict, world_graph: dict, hypothesis: dict, contradictions: dict
) -> dict:
    timeline = "\n".join(
        f"- {item['event_id']}: {item['description']}"
        for item in narrative["sequence_of_events"]
    )
    rows = ["| Hypothesis | Confidence |", "|---|---|"]
    rows.extend(
        f"| {h['title']} | {h['confidence_score']} |" for h in hypothesis["hypotheses"]
    )
    markdown = (
        f"# Narrative Summary\n\nType: {narrative['narrative_type']}\n\n"
        f"## Timeline\n{timeline}\n\n"
        f"## Hypothesis Comparison\n" + "\n".join(rows) + "\n\n"
        "## Contradictions\n"
        f"{len(contradictions['contradictions'])} contradictions detected."
    )
    return {
        "json": {
            "timeline": narrative["sequence_of_events"],
            "entity_summaries": world_graph["entities"],
            "claim_trace": world_graph["claims"],
            "identity_rationale": narrative["template_note"],
            "hypothesis_comparison": hypothesis["hypotheses"],
            "contradiction_report": contradictions,
            "narrative_summary": narrative,
        },
        "markdown": markdown,
    }
