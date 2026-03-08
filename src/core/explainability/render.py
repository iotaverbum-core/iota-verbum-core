from __future__ import annotations

from core.narrative.render import render_narrative_outputs


def build_explainability_payload(
    world_graph: dict,
    narrative: dict,
    identity: dict,
    hypotheses: dict,
    contradictions: dict,
) -> dict:
    rendered = render_narrative_outputs(
        narrative, world_graph, hypotheses, contradictions
    )
    return {
        "timeline": narrative["sequence_of_events"],
        "entity_summaries": world_graph["entities"],
        "claim_trace": world_graph["claims"],
        "identity_rationale": identity["candidates"],
        "hypothesis_comparison_table": hypotheses["hypotheses"],
        "contradiction_report": contradictions["contradictions"],
        "narrative_summary": narrative,
        "evidence_trace_per_conclusion": narrative["supporting_evidence_map"],
        "rendered": rendered,
    }
