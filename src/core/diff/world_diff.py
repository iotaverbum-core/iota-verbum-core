from __future__ import annotations

from core.determinism.schema_validate import validate
from core.diff.change_types import CHANGE_TYPES


def compute_world_diff_v2(old_state: dict, new_state: dict) -> dict:
    old_entities = {e["entity_id"] for e in old_state["world_graph"]["entities"]}
    new_entities = {e["entity_id"] for e in new_state["world_graph"]["entities"]}
    old_events = {e["event_id"] for e in old_state["world_graph"]["events"]}
    new_events = {e["event_id"] for e in new_state["world_graph"]["events"]}
    old_narrative = old_state.get("narrative") or old_state.get(
        "narrative_coherence", {}
    )
    new_narrative = new_state.get("narrative") or new_state.get(
        "narrative_coherence", {}
    )

    result = {
        "schema_version": "2.0",
        "supported_change_types": list(CHANGE_TYPES),
        "old_graph_state": old_state["world_graph"]["graph_sha256"],
        "new_graph_state": new_state["world_graph"]["graph_sha256"],
        "diff_report": {
            "newly_introduced_entities": sorted(new_entities - old_entities),
            "newly_introduced_events": sorted(new_events - old_events),
            "resolved_unknowns": sorted(
                {u["kind"] for u in old_state["world_graph"]["unknowns"]}
                - {u["kind"] for u in new_state["world_graph"]["unknowns"]}
            ),
            "changed_confidence": old_narrative.get("confidence")
            != new_narrative.get("confidence"),
            "changed_contradictions": len(old_state["contradictions"]["contradictions"])
            != len(new_state["contradictions"]["contradictions"]),
            "changed_narrative_posture": old_narrative.get("narrative_type")
            != new_narrative.get("narrative_type"),
            "changed_adjudication_posture": old_state["adjudication"][
                "ranked_final_assessment"
            ]
            != new_state["adjudication"]["ranked_final_assessment"],
        },
    }
    validate(result, "schemas/world_diff_v2.schema.json")
    return result
