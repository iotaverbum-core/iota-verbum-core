from __future__ import annotations


def rank_hypotheses(hypotheses: list[dict], contradictions: list[dict]) -> list[dict]:
    penalty = len(contradictions)
    ranked = []
    for hyp in hypotheses:
        score = max(float(hyp["confidence_score"]) - (0.1 * penalty), 0.0)
        ranked.append(
            {
                "hypothesis_id": hyp["hypothesis_id"],
                "title": hyp["title"],
                "final_score": f"{score:.3f}",
            }
        )
    return sorted(ranked, key=lambda h: (-float(h["final_score"]), h["hypothesis_id"]))
