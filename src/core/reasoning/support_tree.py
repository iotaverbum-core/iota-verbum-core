from __future__ import annotations

from collections import deque

from core.determinism.schema_validate import validate
from core.reasoning.claim_graph import build_claim_graph

SUPPORT_EDGE_TYPES = {"implies", "supports"}


def build_support_tree(
    graph_obj: dict,
    derived_obj: dict,
    target_claim_id: str,
) -> dict:
    graph = build_claim_graph(graph_obj)
    validate(derived_obj, "schemas/derived_edges.schema.json")

    claims_by_id = {
        claim["claim_id"]: claim
        for claim in graph["claims"]
    }
    if target_claim_id not in claims_by_id:
        raise ValueError(f"target claim_id not found: {target_claim_id}")

    primitive_edges = [
        {
            "from_id": edge["from_id"],
            "to_id": edge["to_id"],
            "type": edge["type"],
            "derived": False,
            "proof": None,
        }
        for edge in graph["edges"]
        if edge["type"] in SUPPORT_EDGE_TYPES
    ]
    derived_edges = [
        {
            "from_id": edge["from_id"],
            "to_id": edge["to_id"],
            "type": edge["type"],
            "derived": True,
            "proof": edge["proof"],
        }
        for edge in derived_obj["derived_edges"]
        if edge["type"] in SUPPORT_EDGE_TYPES
    ]
    all_edges = primitive_edges + derived_edges

    reverse_adjacency: dict[str, list[str]] = {}
    contributors: set[str] = {target_claim_id}
    reverse_sets: dict[str, set[str]] = {}
    for edge in all_edges:
        reverse_sets.setdefault(edge["to_id"], set()).add(edge["from_id"])
    reverse_adjacency = {
        claim_id: sorted(source_ids)
        for claim_id, source_ids in sorted(reverse_sets.items())
    }

    queue = deque([target_claim_id])
    visited = {target_claim_id}
    while queue:
        node = queue.popleft()
        for upstream in reverse_adjacency.get(node, []):
            contributors.add(upstream)
            if upstream in visited:
                continue
            visited.add(upstream)
            queue.append(upstream)

    missing_claim_ids = sorted(
        {
            claim_id
            for claim_id in contributors
            if claim_id not in claims_by_id
        }
    )
    if missing_claim_ids:
        raise ValueError(
            "support tree missing claims for ids: " + ", ".join(missing_claim_ids)
        )

    nodes = [
        {
            "claim_id": claim_id,
            "claim": claims_by_id[claim_id],
        }
        for claim_id in sorted(contributors)
    ]
    edges = sorted(
        [
            edge
            for edge in all_edges
            if edge["from_id"] in contributors and edge["to_id"] in contributors
        ],
        key=lambda edge: (edge["type"], edge["from_id"], edge["to_id"]),
    )

    support_tree = {
        "support_tree_version": "1.0",
        "target_claim_id": target_claim_id,
        "nodes": nodes,
        "edges": edges,
    }
    validate(support_tree, "schemas/support_tree.schema.json")
    return support_tree
