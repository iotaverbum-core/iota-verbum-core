from __future__ import annotations

from core.determinism.schema_validate import validate


def build_verification_report(
    world_graph: dict,
    identity: dict,
    hypotheses: dict,
    narrative: dict,
    contradictions: dict,
    adjudication: dict,
) -> dict:
    unresolved = sorted({u["kind"] for u in world_graph["unknowns"]})
    issues = []
    if not world_graph["entities"]:
        issues.append("no_entities")
    if not hypotheses["hypotheses"]:
        issues.append("no_hypotheses")
    result = {
        "schema_version": "2.0",
        "graph_integrity": len(world_graph["entities"]) > 0
        and len(world_graph["events"]) > 0,
        "claim_support": len(world_graph["claims"]) > 0,
        "identity_support": len(identity["candidates"]) > 0,
        "hypothesis_support": len(hypotheses["hypotheses"]) > 0,
        "narrative_coherence_support": len(narrative["sequence_of_events"]) > 0,
        "contradiction_resolution_quality": "sufficient"
        if not contradictions["contradictions"]
        else "requires_review",
        "evidence_sufficiency": "sufficient" if not unresolved else "insufficient",
        "provenance_completeness": all(
            "source_ref" in event for event in world_graph["events"]
        ),
        "verification_report": {"issues": sorted(issues)},
        "unresolved_issues": unresolved,
        "insufficiency_report": unresolved,
        "continuity_report": {"graph_version": world_graph["graph_version"]},
        "provenance_audit_report": {
            "event_refs": len(world_graph["events"]),
            "claim_refs": len(world_graph["claims"]),
        },
        "adjudication_snapshot": adjudication["ranked_final_assessment"],
    }
    validate(result, "schemas/verification_v2.schema.json")
    return result
