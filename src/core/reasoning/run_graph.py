from __future__ import annotations

from core.determinism.finalize import finalize
from core.determinism.ledger import write_run
from core.reasoning.claim_graph import (
    build_claim_graph,
    find_duplicates_and_contradictions,
)
from core.reasoning.closure import compute_closure
from core.reasoning.narrative import render_narrative
from core.reasoning.support_tree import build_support_tree


def build_graph_reasoning_output(
    claim_graph_obj: dict,
    *,
    target_claim_id: str | None = None,
) -> dict:
    claim_graph = build_claim_graph(claim_graph_obj)
    findings = find_duplicates_and_contradictions(claim_graph)
    derived = compute_closure(claim_graph)
    output_obj = {
        "claim_graph": claim_graph,
        "findings": findings,
        "derived": derived,
    }
    if target_claim_id is not None:
        support_tree = build_support_tree(
            claim_graph,
            derived,
            target_claim_id,
        )
        output_obj["support_tree"] = support_tree
        output_obj["narrative"] = render_narrative(
            support_tree=support_tree,
            findings=findings,
        )
    return output_obj


def run_graph_reasoning(
    evidence_bundle_obj: dict,
    claim_graph_obj: dict,
    *,
    manifest_sha256: str,
    core_version: str,
    ruleset_id: str,
    created_utc: str,
    ledger_root: str | None = None,
    target_claim_id: str | None = None,
) -> dict:
    output_obj = build_graph_reasoning_output(
        claim_graph_obj,
        target_claim_id=target_claim_id,
    )
    sealed = finalize(
        evidence_bundle_obj,
        output_obj,
        manifest_sha256=manifest_sha256,
        core_version=core_version,
        ruleset_id=ruleset_id,
        created_utc=created_utc,
    )
    if ledger_root is not None:
        run_dir = write_run(ledger_root=ledger_root, **sealed)
        return {
            **sealed,
            "ledger_dir": str(run_dir),
        }
    return sealed
