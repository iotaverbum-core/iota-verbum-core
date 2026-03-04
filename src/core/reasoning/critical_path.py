from __future__ import annotations

from collections import deque

from core.determinism.schema_validate import validate

_INFLUENCE_EDGE_TYPES = ("before", "causes", "enables")


def _adjacency_for_types(
    causal_graph: dict,
    edge_types: tuple[str, ...],
) -> tuple[dict[str, list[str]], list[dict]]:
    nodes = list(causal_graph["nodes"])
    adjacency = {node_id: [] for node_id in nodes}
    edges = [
        edge
        for edge in causal_graph["edges"]
        if edge["type"] in edge_types
    ]
    for edge in edges:
        adjacency[edge["from_event_id"]].append(edge["to_event_id"])
    for node_id in adjacency:
        adjacency[node_id] = sorted(set(adjacency[node_id]))
    return adjacency, sorted(
        edges,
        key=lambda edge: (
            edge["type"],
            edge["from_event_id"],
            edge["to_event_id"],
        ),
    )


def _downstream_reach(adjacency: dict[str, list[str]], start: str) -> int:
    visited: set[str] = set()
    queue: deque[str] = deque(adjacency[start])
    while queue:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)
        for next_node in adjacency[node_id]:
            if next_node not in visited:
                queue.append(next_node)
    return len(visited)


def _top_events(
    nodes: list[str],
    adjacency: dict[str, list[str]],
    *,
    top_k: int,
) -> list[dict]:
    scored = []
    for node_id in nodes:
        fan_out = len(adjacency[node_id])
        downstream_reach = _downstream_reach(adjacency, node_id)
        score = (fan_out * 10) + downstream_reach
        scored.append(
            {
                "event_id": node_id,
                "score": score,
                "fan_out": fan_out,
                "downstream_reach": downstream_reach,
            }
        )
    scored.sort(key=lambda item: (-item["score"], item["event_id"]))
    return scored[:top_k]


def _longest_before_chain(causal_graph: dict) -> tuple[list[str], bool]:
    adjacency, before_edges = _adjacency_for_types(causal_graph, ("before",))
    nodes = list(causal_graph["nodes"])
    indegree = {node_id: 0 for node_id in nodes}
    for edge in before_edges:
        indegree[edge["to_event_id"]] += 1

    available = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
    topo_order: list[str] = []
    while available:
        node_id = available.pop(0)
        topo_order.append(node_id)
        for next_node in adjacency[node_id]:
            indegree[next_node] -= 1
            if indegree[next_node] == 0:
                available.append(next_node)
                available.sort()

    if len(topo_order) != len(nodes):
        return [], True

    best_by_node = {node_id: [node_id] for node_id in nodes}
    for node_id in reversed(topo_order):
        candidates = [[node_id]]
        for next_node in adjacency[node_id]:
            candidates.append([node_id, *best_by_node[next_node]])
        best_by_node[node_id] = min(
            candidates,
            key=lambda chain: (-len(chain), tuple(chain)),
        )

    best_chain = min(
        (best_by_node[node_id] for node_id in nodes),
        key=lambda chain: (-len(chain), tuple(chain)),
    )
    return best_chain, False


def compute_critical_path(causal_graph: dict, *, top_k: int = 5) -> dict:
    validate(causal_graph, "schemas/causal_graph.schema.json")

    nodes = list(causal_graph["nodes"])
    influence_adjacency, influence_edges = _adjacency_for_types(
        causal_graph,
        _INFLUENCE_EDGE_TYPES,
    )
    critical_chain, cycle_detected = _longest_before_chain(causal_graph)
    critical_path = {
        "version": "1.0",
        "top_k": top_k,
        "top_events": _top_events(nodes, influence_adjacency, top_k=top_k),
        "critical_chain": critical_chain,
        "receipts": {
            "edge_types_used": list(_INFLUENCE_EDGE_TYPES),
            "counts": {
                "nodes": len(nodes),
                "edges": len(influence_edges),
            },
        },
    }
    if cycle_detected:
        critical_path["receipts"]["cycle_detected"] = True
    validate(critical_path, "schemas/critical_path.schema.json")
    return critical_path
