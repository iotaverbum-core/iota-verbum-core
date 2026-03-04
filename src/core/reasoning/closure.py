from __future__ import annotations

from collections import deque

from core.determinism.schema_validate import validate
from core.reasoning.claim_graph import build_claim_graph

TRANSITIVE_EDGE_TYPES = ("depends_on", "implies", "supports")


def build_adjacency(edges, edge_type) -> dict[str, list[str]]:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        if edge["type"] != edge_type:
            continue
        adjacency.setdefault(edge["from_id"], set()).add(edge["to_id"])

    return {
        node: sorted(targets)
        for node, targets in sorted(adjacency.items())
    }


def _edge_lookup(edges, edge_type: str) -> dict[tuple[str, str], dict]:
    lookup = {}
    for edge in edges:
        if edge["type"] == edge_type:
            lookup[(edge["from_id"], edge["to_id"])] = {
                "from_id": edge["from_id"],
                "to_id": edge["to_id"],
                "type": edge["type"],
            }
    return lookup


def _shortest_path(
    adjacency: dict[str, list[str]],
    source: str,
    target: str,
) -> list[tuple[str, str]] | None:
    queue = deque([(source, [])])
    visited = {source}
    while queue:
        node, path = queue.popleft()
        for neighbor in adjacency.get(node, []):
            next_path = path + [(node, neighbor)]
            if neighbor == target:
                return next_path
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append((neighbor, next_path))
    return None


def compute_closure(graph_obj: dict) -> dict:
    graph = build_claim_graph(graph_obj)
    primitive_edges = list(graph["edges"])
    primitive_index = {
        (edge["type"], edge["from_id"], edge["to_id"])
        for edge in primitive_edges
    }
    derived_edges = []

    for edge_type in TRANSITIVE_EDGE_TYPES:
        adjacency = build_adjacency(primitive_edges, edge_type)
        lookup = _edge_lookup(primitive_edges, edge_type)
        nodes = sorted(
            {
                edge["from_id"]
                for edge in primitive_edges
                if edge["type"] == edge_type
            }
            | {
                edge["to_id"]
                for edge in primitive_edges
                if edge["type"] == edge_type
            }
        )

        for source in nodes:
            for target in nodes:
                if source == target:
                    continue
                key = (edge_type, source, target)
                if key in primitive_index:
                    continue
                path = _shortest_path(adjacency, source, target)
                if path is None or len(path) < 2:
                    continue
                proof = [lookup[(from_id, to_id)] for from_id, to_id in path]
                derived_edges.append(
                    {
                        "from_id": source,
                        "to_id": target,
                        "type": edge_type,
                        "proof": proof,
                    }
                )

    result = {
        "derived_version": "1.0",
        "derived_edges": sorted(
            derived_edges,
            key=lambda item: (item["type"], item["from_id"], item["to_id"]),
        ),
    }
    validate(result, "schemas/derived_edges.schema.json")
    return result
