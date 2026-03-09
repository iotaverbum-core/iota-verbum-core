from __future__ import annotations

from core.adjudication import run_adjudication
from core.contradiction import detect_contradictions
from core.explainability import build_explainability_payload
from core.hypothesis import run_hypothesis_competition
from core.identity import run_identity_engine
from core.ledger import seal_run
from core.narrative import compute_narrative_coherence
from core.semantic import extract_semantic_artifacts
from core.verification import build_verification_report
from core.world import build_world_graph


def run_narrative_intelligence_v2(evidence_pack: dict, run_config: dict) -> dict:
    semantic = extract_semantic_artifacts(evidence_pack)
    world_graph = build_world_graph(semantic)
    identity = run_identity_engine(world_graph)
    hypotheses = run_hypothesis_competition(world_graph)
    narrative = compute_narrative_coherence(world_graph, identity, hypotheses)
    contradictions = detect_contradictions(world_graph, identity, hypotheses, narrative)
    adjudication = run_adjudication(hypotheses, contradictions)
    verification = build_verification_report(
        world_graph, identity, hypotheses, narrative, contradictions, adjudication
    )
    explainability = build_explainability_payload(
        world_graph, narrative, identity, hypotheses, contradictions
    )
    stages = {
        "semantic_extraction": semantic,
        "world_graph": world_graph,
        "identity": identity,
        "hypothesis_competition": hypotheses,
        "narrative_coherence": narrative,
        "contradictions": contradictions,
        "adjudication": adjudication,
        "verification": verification,
        "explainability": explainability,
    }
    sealed = seal_run(stages, run_config)
    return {**stages, "ledger": sealed}
