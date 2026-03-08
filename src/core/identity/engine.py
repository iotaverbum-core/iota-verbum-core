from __future__ import annotations

from core.determinism.schema_validate import validate
from core.identity.patterns import PATTERNS
from core.identity.scoring import to_confidence


def run_identity_engine(world_graph: dict) -> dict:
    corpus = " ".join(
        [event["description"].lower() for event in world_graph["events"]]
        + [claim["text"].lower() for claim in world_graph["claims"]]
    )
    candidates = []
    for pattern, terms in sorted(PATTERNS.items()):
        support = [term for term in sorted(terms) if term in corpus]
        contradiction = [term for term in sorted(terms) if term not in corpus]
        candidates.append(
            {
                "identity": pattern,
                "confidence": to_confidence(len(support), len(terms)),
                "support": support,
                "contradictions": contradiction,
                "evidence_refs": sorted(
                    {event["source_ref"]["chunk_id"] for event in world_graph["events"]}
                ),
                "rationale_trace": f"matched {len(support)} of {len(terms)} keywords",
            }
        )
    result = {
        "schema_version": "2.0",
        "candidates": sorted(
            candidates, key=lambda c: (-float(c["confidence"]), c["identity"])
        ),
    }
    validate(result, "schemas/identity_result.schema.json")
    return result
