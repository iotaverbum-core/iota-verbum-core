from __future__ import annotations

from core.contradiction.classes import CONTRADICTION_CLASSES
from core.determinism.schema_validate import validate


def detect_contradictions(
    world_graph: dict, identity_result: dict, hypothesis_result: dict, narrative: dict
) -> dict:
    contradictions = []
    if world_graph["unknowns"]:
        contradictions.append(
            {
                "class": "evidentiary_insufficiency",
                "reason": "unknown fields present",
                "refs": world_graph["unknowns"],
            }
        )
    if (
        narrative["narrative_type"] == "cover-up"
        and identity_result["candidates"]
        and identity_result["candidates"][0]["identity"] == "compliance"
    ):
        contradictions.append(
            {
                "class": "identity_contradiction",
                "reason": "cover-up narrative conflicts with compliance identity",
                "refs": ["narrative", "identity"],
            }
        )
    if (
        len(hypothesis_result["hypotheses"]) >= 2
        and hypothesis_result["hypotheses"][0]["confidence_score"]
        == hypothesis_result["hypotheses"][1]["confidence_score"]
    ):
        contradictions.append(
            {
                "class": "exclusive_narrative_contradiction",
                "reason": "top hypotheses tied",
                "refs": [
                    hypothesis_result["hypotheses"][0]["hypothesis_id"],
                    hypothesis_result["hypotheses"][1]["hypothesis_id"],
                ],
            }
        )

    result = {
        "schema_version": "2.0",
        "supported_classes": list(CONTRADICTION_CLASSES),
        "contradictions": sorted(
            contradictions, key=lambda c: (c["class"], c["reason"])
        ),
    }
    validate(result, "schemas/contradiction_result.schema.json")
    return result
