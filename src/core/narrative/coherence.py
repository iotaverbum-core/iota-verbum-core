from __future__ import annotations

from core.determinism.schema_validate import validate
from core.narrative.sequence import build_sequence
from core.narrative.templates import TEMPLATES


def compute_narrative_coherence(
    world_graph: dict, identity_result: dict, hypothesis_result: dict
) -> dict:
    sequence = build_sequence(world_graph)
    top_hyp = (
        hypothesis_result["hypotheses"][0] if hypothesis_result["hypotheses"] else None
    )
    narrative_type = "failure_of_oversight"
    if top_hyp and "fraud" in top_hyp["title"].lower():
        narrative_type = "cover-up"
    key_actors = [entity["canonical_name"] for entity in world_graph["entities"][:5]]
    unresolved = [u["kind"] for u in world_graph["unknowns"]]
    result = {
        "schema_version": "2.0",
        "narrative_type": narrative_type,
        "sequence_of_events": sequence,
        "key_actors": key_actors,
        "turning_points": [
            s
            for s in sequence
            if "failed" in s["description"].lower()
            or "restored" in s["description"].lower()
        ],
        "unresolved_tensions": unresolved,
        "confidence": identity_result["candidates"][0]["confidence"]
        if identity_result["candidates"]
        else "0.000",
        "supporting_evidence_map": {
            event["event_id"]: event["source_ref"] for event in world_graph["events"]
        },
        "template_note": TEMPLATES[narrative_type],
    }
    validate(result, "schemas/narrative_coherence.schema.json")
    return result
