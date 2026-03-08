from __future__ import annotations

from core.hypothesis.models import HYPOTHESIS_LIBRARY


def generate_hypotheses(world_graph: dict) -> list[dict]:
    corpus = " ".join(
        [e["description"].lower() for e in world_graph["events"]]
        + [c["text"].lower() for c in world_graph["claims"]]
    )
    hypotheses = []
    for hyp_id, title, assumptions in HYPOTHESIS_LIBRARY:
        support = [term for term in assumptions if term in corpus]
        contradict = [term for term in assumptions if term not in corpus]
        hypotheses.append(
            {
                "hypothesis_id": hyp_id,
                "title": title,
                "description": title,
                "assumptions": assumptions,
                "supporting_evidence": support,
                "contradicting_evidence": contradict,
                "missing_evidence": contradict,
            }
        )
    return sorted(hypotheses, key=lambda h: h["hypothesis_id"])
