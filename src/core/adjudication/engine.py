from __future__ import annotations

from core.adjudication.ranking import rank_hypotheses
from core.determinism.schema_validate import validate


def run_adjudication(hypothesis_result: dict, contradiction_result: dict) -> dict:
    ranked = rank_hypotheses(
        hypothesis_result["hypotheses"], contradiction_result["contradictions"]
    )
    viable = [r for r in ranked if float(r["final_score"]) > 0]
    eliminated = [r for r in ranked if float(r["final_score"]) <= 0]
    result = {
        "schema_version": "2.0",
        "viable_explanations": viable,
        "eliminated_explanations": eliminated,
        "resolution_evidence_needed": [
            "direct transaction records",
            "independent witness evidence",
        ],
        "ranked_final_assessment": ranked,
    }
    validate(result, "schemas/adjudication_result.schema.json")
    return result
