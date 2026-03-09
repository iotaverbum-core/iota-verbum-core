from __future__ import annotations

from core.determinism.schema_validate import validate
from core.hypothesis.generator import generate_hypotheses
from core.hypothesis.scoring import score_ratio


def run_hypothesis_competition(world_graph: dict) -> dict:
    hypotheses = []
    for hyp in generate_hypotheses(world_graph):
        total = len(hyp["assumptions"])
        support_n = len(hyp["supporting_evidence"])
        contradiction_n = len(hyp["contradicting_evidence"])
        hypotheses.append(
            {
                **hyp,
                "confidence_score": score_ratio(support_n, total),
                "causal_plausibility_score": score_ratio(
                    max(support_n - contradiction_n, 0), total
                ),
                "temporal_fit_score": score_ratio(
                    sum(1 for e in world_graph["events"] if e.get("temporal_anchor")),
                    max(len(world_graph["events"]), 1),
                ),
                "source_reliability_score": "1.000"
                if world_graph.get("events")
                else "0.000",
            }
        )
    ranked = sorted(
        hypotheses, key=lambda h: (-float(h["confidence_score"]), h["hypothesis_id"])
    )
    result = {"schema_version": "2.0", "hypotheses": ranked}
    validate(result, "schemas/hypothesis_result.schema.json")
    return result
