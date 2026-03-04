from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from itertools import combinations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.schema_validate import validate

_BACKTICK_RE = re.compile(r"`([^`]+)`")
_UPPER_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
_WORD_RE = re.compile(r"[a-z0-9]+")

_CONFIDENCE_BY_REASON = {
    "RULE_TIME_EXPLICIT_DATE": "high",
    "RULE_TIME_PHRASE_BEFORE": "medium",
    "RULE_POLICY_PRECEDES_CONFIG": "high",
    "RULE_SECRET_HANDLING_CAUSAL": "high",
    "RULE_CONFLICT_IMPLIED": "high",
}
_REASON_PRIORITY = {
    "RULE_CONFLICT_IMPLIED": 0,
    "RULE_SECRET_HANDLING_CAUSAL": 1,
    "RULE_POLICY_PRECEDES_CONFIG": 2,
    "RULE_TIME_PHRASE_BEFORE": 3,
    "RULE_TIME_EXPLICIT_DATE": 4,
}
_PHRASE_TERMS = {
    "before": "forward",
    "prior to": "forward",
    "after": "inverse",
    "following": "inverse",
}
_EVENT_TYPE_TERMS = {
    "Access": ("access", "login"),
    "Config": ("config", "configuration", "environment"),
    "Deployment": ("deployment", "deploy"),
    "Leak": ("leak", "breach", "exposed"),
    "Other": (),
    "PolicyChange": ("policy", "policy change"),
    "Rotation": ("rotation", "rotate", "rotated"),
}
_SECRET_NEVER_TERMS = ("never in source", "never in repo")
_SECRET_ENV_TERMS = ("environment only", "env-only")


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    return normalized.replace("\r\n", "\n").replace("\r", "\n")


def _sort_evidence_refs(evidence_refs: list[dict]) -> list[dict]:
    unique_refs = {
        (
            evidence_ref["source_id"],
            evidence_ref["chunk_id"],
            evidence_ref["offset_start"],
            evidence_ref["offset_end"],
            evidence_ref["text_sha256"],
        ): evidence_ref
        for evidence_ref in evidence_refs
    }
    return [unique_refs[key] for key in sorted(unique_refs)]


def _event_time_key(event: dict) -> str:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return "~" + event["event_id"]
    return time_ref["value"]


def _event_sort_key(event: dict) -> tuple[str, str]:
    return (_event_time_key(event), event["event_id"])


def _normalized_text(event: dict) -> str:
    state_text = ""
    if event["state"] is not None:
        state_text = " " + dumps_canonical(event["state"]).decode("utf-8")
    return _normalize_text(event["action"] + state_text).lower()


def _canonical_token(token: str) -> str:
    normalized = _normalize_text(token).strip()
    if not normalized:
        return ""
    if normalized.startswith("entity:"):
        return normalized
    return normalized.upper()


def _extract_object_tokens(event: dict) -> list[str]:
    tokens = {_canonical_token(token) for token in event["objects"]}
    text = event["action"]
    if event["state"] is not None:
        text += " " + dumps_canonical(event["state"]).decode("utf-8")
    for token in _BACKTICK_RE.findall(text):
        canonical = _canonical_token(token)
        if canonical:
            tokens.add(canonical)
    for token in _UPPER_TOKEN_RE.findall(text):
        canonical = _canonical_token(token)
        if canonical:
            tokens.add(canonical)
    return sorted(tokens)


def _target_terms(event: dict) -> list[str]:
    terms = set(_EVENT_TYPE_TERMS[event["type"]])
    normalized = _normalized_text(event)
    for word in _WORD_RE.findall(normalized):
        if len(word) >= 4:
            terms.add(word)
    for token in _extract_object_tokens(event):
        if token.startswith("entity:"):
            continue
        terms.add(token.lower())
    return sorted(terms)


def _unknowns_by_event(world_model: dict) -> dict[str, set[str]]:
    unknowns_by_event: dict[str, set[str]] = defaultdict(set)
    for unknown in world_model["unknowns"]:
        event_id = unknown["ref"].get("event_id")
        if isinstance(event_id, str):
            unknowns_by_event[event_id].add(unknown["kind"])
    return dict(unknowns_by_event)


def _shared_object_tokens(left: dict, right: dict) -> list[str]:
    return sorted(
        set(_extract_object_tokens(left)).intersection(_extract_object_tokens(right))
    )


def _build_unknown_block_finding(
    *,
    left: dict,
    right: dict,
    reason_code: str,
    missing_kinds: set[str],
) -> dict:
    event_ids = sorted((left["event_id"], right["event_id"]))
    details = {
        "missing_kinds": sorted(missing_kinds),
        "reason_code": reason_code,
    }
    return {
        "code": "UNKNOWN_BLOCKS_CAUSAL",
        "message": (
            f"{reason_code} cannot be inferred deterministically because required "
            + ", ".join(sorted(missing_kinds))
            + " is missing"
        ),
        "event_ids": event_ids,
        "details": details,
    }


def _before_edge(
    *,
    from_event_id: str,
    to_event_id: str,
    reason_code: str,
    evidence: list[dict],
) -> dict:
    edge = {
        "from_event_id": from_event_id,
        "to_event_id": to_event_id,
        "type": "before",
        "reason_code": reason_code,
        "confidence": _CONFIDENCE_BY_REASON[reason_code],
        "evidence": _sort_evidence_refs(evidence),
    }
    validate(edge, "schemas/causal_edge.schema.json")
    return edge


def _edge_from_rule(
    *,
    from_event_id: str,
    to_event_id: str,
    edge_type: str,
    reason_code: str,
    evidence: list[dict],
) -> dict:
    edge = {
        "from_event_id": from_event_id,
        "to_event_id": to_event_id,
        "type": edge_type,
        "reason_code": reason_code,
        "confidence": _CONFIDENCE_BY_REASON[reason_code],
        "evidence": _sort_evidence_refs(evidence),
    }
    validate(edge, "schemas/causal_edge.schema.json")
    return edge


def _register_edge(edges_by_key: dict[tuple[str, str, str], dict], edge: dict) -> None:
    key = (edge["from_event_id"], edge["to_event_id"], edge["type"])
    existing = edges_by_key.get(key)
    if existing is None:
        edges_by_key[key] = edge
        return
    merged_evidence = _sort_evidence_refs(existing["evidence"] + edge["evidence"])
    keep_existing = _REASON_PRIORITY[existing["reason_code"]] <= _REASON_PRIORITY[
        edge["reason_code"]
    ]
    chosen = existing if keep_existing else edge
    edges_by_key[key] = {
        **chosen,
        "evidence": merged_evidence,
    }


def _add_finding(findings_by_key: dict[tuple[str, str], dict], finding: dict) -> None:
    key = (finding["code"], _sort_key(finding))
    findings_by_key[key] = finding


def _phrase_relation(source: dict, target: dict) -> tuple[str, str] | None:
    if source["event_id"] == target["event_id"]:
        return None
    source_text = _normalized_text(source)
    target_terms = _target_terms(target)
    if not target_terms:
        return None

    for phrase, direction in _PHRASE_TERMS.items():
        for term in target_terms:
            marker = f"{phrase} {term}"
            if marker not in source_text:
                continue
            if direction == "forward":
                return (source["event_id"], target["event_id"])
            return (target["event_id"], source["event_id"])

    for term in target_terms:
        if f"then {term}" in source_text:
            return (source["event_id"], target["event_id"])
        if f"when {term} ended" in source_text:
            return (target["event_id"], source["event_id"])
    return None


def _tarjan_cycle_nodes(
    node_ids: list[str],
    before_edges: list[dict],
) -> list[str]:
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in before_edges:
        adjacency[edge["from_event_id"]].append(edge["to_event_id"])
    for node_id in adjacency:
        adjacency[node_id].sort()

    index = 0
    stack: list[str] = []
    index_by_node: dict[str, int] = {}
    lowlink_by_node: dict[str, int] = {}
    on_stack: set[str] = set()
    cycle_nodes: set[str] = set()

    def strongconnect(node_id: str) -> None:
        nonlocal index
        index_by_node[node_id] = index
        lowlink_by_node[node_id] = index
        index += 1
        stack.append(node_id)
        on_stack.add(node_id)

        for next_node in adjacency[node_id]:
            if next_node not in index_by_node:
                strongconnect(next_node)
                lowlink_by_node[node_id] = min(
                    lowlink_by_node[node_id],
                    lowlink_by_node[next_node],
                )
            elif next_node in on_stack:
                lowlink_by_node[node_id] = min(
                    lowlink_by_node[node_id],
                    index_by_node[next_node],
                )

        if lowlink_by_node[node_id] != index_by_node[node_id]:
            return

        component = []
        while stack:
            current = stack.pop()
            on_stack.remove(current)
            component.append(current)
            if current == node_id:
                break
        component.sort()
        if len(component) > 1:
            cycle_nodes.update(component)
        elif component and component[0] in adjacency[component[0]]:
            cycle_nodes.add(component[0])

    for node_id in sorted(node_ids):
        if node_id not in index_by_node:
            strongconnect(node_id)
    return sorted(cycle_nodes)


def _compute_causal_order(
    node_ids: list[str],
    events_by_id: dict[str, dict],
    before_edges: list[dict],
) -> list[str]:
    indegree = {node_id: 0 for node_id in node_ids}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in before_edges:
        adjacency[edge["from_event_id"]].append(edge["to_event_id"])
        indegree[edge["to_event_id"]] += 1
    for node_id in adjacency:
        adjacency[node_id].sort()

    available = sorted(
        [node_id for node_id, degree in indegree.items() if degree == 0],
        key=lambda node_id: _event_sort_key(events_by_id[node_id]),
    )
    order = []
    while available:
        node_id = available.pop(0)
        order.append(node_id)
        for next_node in adjacency[node_id]:
            indegree[next_node] -= 1
            if indegree[next_node] == 0:
                available.append(next_node)
                available.sort(key=lambda item: _event_sort_key(events_by_id[item]))
    if len(order) != len(node_ids):
        return []
    return order


def compute_causal_graph(world_model: dict) -> dict:
    validate(world_model, "schemas/world_model.schema.json")

    events = sorted(world_model["events"], key=_event_sort_key)
    events_by_id = {event["event_id"]: event for event in events}
    node_ids = [event["event_id"] for event in events]
    unknowns_by_event = _unknowns_by_event(world_model)
    edges_by_key: dict[tuple[str, str, str], dict] = {}
    findings_by_key: dict[tuple[str, str], dict] = {}

    known_events = [event for event in events if event["time"]["kind"] != "unknown"]
    for left, right in combinations(known_events, 2):
        left_value = left["time"]["value"]
        right_value = right["time"]["value"]
        if left_value == right_value:
            continue
        ordered = (left, right) if left_value < right_value else (right, left)
        _register_edge(
            edges_by_key,
            _before_edge(
                from_event_id=ordered[0]["event_id"],
                to_event_id=ordered[1]["event_id"],
                reason_code="RULE_TIME_EXPLICIT_DATE",
                evidence=ordered[0]["evidence"] + ordered[1]["evidence"],
            ),
        )

    for left, right in combinations(events, 2):
        pair_missing_unknowns = (
            unknowns_by_event.get(left["event_id"], set())
            | unknowns_by_event.get(right["event_id"], set())
        )
        shared_tokens = _shared_object_tokens(left, right)

        if left["type"] == "PolicyChange" and right["type"] == "Config":
            if shared_tokens:
                _register_edge(
                    edges_by_key,
                    _before_edge(
                        from_event_id=left["event_id"],
                        to_event_id=right["event_id"],
                        reason_code="RULE_POLICY_PRECEDES_CONFIG",
                        evidence=left["evidence"] + right["evidence"],
                    ),
                )
            elif "missing_object" in pair_missing_unknowns:
                _add_finding(
                    findings_by_key,
                    _build_unknown_block_finding(
                        left=left,
                        right=right,
                        reason_code="RULE_POLICY_PRECEDES_CONFIG",
                        missing_kinds={"missing_object"},
                    ),
                )

        if "missing_object" in pair_missing_unknowns and (
            any(term in _normalized_text(left) for term in _SECRET_NEVER_TERMS)
            or any(term in _normalized_text(right) for term in _SECRET_NEVER_TERMS)
            or any(term in _normalized_text(left) for term in _SECRET_ENV_TERMS)
            or any(term in _normalized_text(right) for term in _SECRET_ENV_TERMS)
        ):
            _add_finding(
                findings_by_key,
                _build_unknown_block_finding(
                    left=left,
                    right=right,
                    reason_code="RULE_SECRET_HANDLING_CAUSAL",
                    missing_kinds={"missing_object"},
                ),
            )
        elif shared_tokens:
            left_text = _normalized_text(left)
            right_text = _normalized_text(right)
            left_is_never = any(term in left_text for term in _SECRET_NEVER_TERMS)
            right_is_never = any(term in right_text for term in _SECRET_NEVER_TERMS)
            left_is_env = any(term in left_text for term in _SECRET_ENV_TERMS)
            right_is_env = any(term in right_text for term in _SECRET_ENV_TERMS)
            if left_is_never and right_is_env:
                _register_edge(
                    edges_by_key,
                    _edge_from_rule(
                        from_event_id=left["event_id"],
                        to_event_id=right["event_id"],
                        edge_type="enables",
                        reason_code="RULE_SECRET_HANDLING_CAUSAL",
                        evidence=left["evidence"] + right["evidence"],
                    ),
                )
            elif right_is_never and left_is_env:
                _register_edge(
                    edges_by_key,
                    _edge_from_rule(
                        from_event_id=right["event_id"],
                        to_event_id=left["event_id"],
                        edge_type="enables",
                        reason_code="RULE_SECRET_HANDLING_CAUSAL",
                        evidence=left["evidence"] + right["evidence"],
                    ),
                )

        if shared_tokens:
            left_relation = _phrase_relation(left, right)
            if left_relation is not None:
                _register_edge(
                    edges_by_key,
                    _before_edge(
                        from_event_id=left_relation[0],
                        to_event_id=left_relation[1],
                        reason_code="RULE_TIME_PHRASE_BEFORE",
                        evidence=left["evidence"] + right["evidence"],
                    ),
                )
            right_relation = _phrase_relation(right, left)
            if right_relation is not None:
                _register_edge(
                    edges_by_key,
                    _before_edge(
                        from_event_id=right_relation[0],
                        to_event_id=right_relation[1],
                        reason_code="RULE_TIME_PHRASE_BEFORE",
                        evidence=left["evidence"] + right["evidence"],
                    ),
                )

    for conflict in sorted(
        world_model["conflicts"],
        key=lambda item: (item["kind"], _sort_key(item["ref"])),
    ):
        event_ids = conflict["ref"].get("event_ids", [])
        if not isinstance(event_ids, list):
            continue
        valid_event_ids = sorted(
            event_id for event_id in event_ids if event_id in events_by_id
        )
        for from_event_id, to_event_id in combinations(valid_event_ids, 2):
            _register_edge(
                edges_by_key,
                _edge_from_rule(
                    from_event_id=from_event_id,
                    to_event_id=to_event_id,
                    edge_type="contradicts",
                    reason_code="RULE_CONFLICT_IMPLIED",
                    evidence=(
                        events_by_id[from_event_id]["evidence"]
                        + events_by_id[to_event_id]["evidence"]
                    ),
                ),
            )

    edges = sorted(
        edges_by_key.values(),
        key=lambda edge: (
            edge["type"],
            edge["from_event_id"],
            edge["to_event_id"],
            edge["reason_code"],
            _sort_key({"evidence": edge["evidence"]}),
        ),
    )
    before_edges = [edge for edge in edges if edge["type"] == "before"]
    cycle_nodes = _tarjan_cycle_nodes(node_ids, before_edges)
    if cycle_nodes:
        _add_finding(
            findings_by_key,
            {
                "code": "CYCLE_TEMPORAL_CONSTRAINT",
                "message": "Temporal before edges contain a cycle",
                "event_ids": cycle_nodes,
                "details": {
                    "edge_count": len(before_edges),
                },
            },
        )

    findings = [
        findings_by_key[key]
        for key in sorted(
            findings_by_key,
            key=lambda item: (
                item[0],
                item[1],
            ),
        )
    ]
    validate(findings, "schemas/causal_findings.schema.json")
    causal_graph = {
        "version": "1.0",
        "nodes": node_ids,
        "edges": edges,
        "causal_order": _compute_causal_order(node_ids, events_by_id, before_edges),
        "findings": findings,
    }
    if cycle_nodes:
        causal_graph["causal_order"] = []
    validate(causal_graph, "schemas/causal_graph.schema.json")
    return causal_graph
