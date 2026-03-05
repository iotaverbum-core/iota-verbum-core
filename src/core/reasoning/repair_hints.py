from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _time_value(event: dict) -> str | None:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return None
    return time_ref["value"]


def _event_time_sort_key(event: dict) -> tuple[int, str, str]:
    time_value = _time_value(event)
    if time_value is None:
        return (1, "", event["event_id"])
    return (0, time_value, event["event_id"])


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


def _sort_related_edges(related_edges: list[dict]) -> list[dict]:
    unique_edges = {
        (
            edge["from_event_id"],
            edge["to_event_id"],
            edge["type"],
        ): edge
        for edge in related_edges
    }
    return [unique_edges[key] for key in sorted(unique_edges)]


def _collect_related_edges(causal_graph: dict, violation: dict) -> list[dict]:
    event_ids = set(violation["events"])
    related_edges = []
    for edge in causal_graph["edges"]:
        if edge["from_event_id"] not in event_ids:
            continue
        if edge["to_event_id"] not in event_ids:
            continue
        related_edges.append(
            {
                "from_event_id": edge["from_event_id"],
                "to_event_id": edge["to_event_id"],
                "type": edge["type"],
            }
        )
    return _sort_related_edges(related_edges)


def _select_time_unknown_target(
    violation: dict,
    events_by_id: dict[str, dict],
) -> list[str]:
    explicit_events = [
        events_by_id[event_id]
        for event_id in violation["events"]
        if _time_value(events_by_id[event_id]) is not None
    ]
    if not explicit_events:
        return sorted(violation["events"])
    explicit_events = sorted(explicit_events, key=_event_time_sort_key)
    return [explicit_events[0]["event_id"]]


def _build_hint(
    *,
    violation_type: str,
    event_ids: list[str],
    entity_ids: list[str],
    action: str,
    rationale: str,
    risk: str,
    violation_receipts: list[dict],
    related_edges: list[dict],
) -> dict:
    hint = {
        "hint_id": "",
        "violation_type": violation_type,
        "target": {
            "event_ids": sorted(event_ids),
            "entity_ids": sorted(entity_ids),
        },
        "action": action,
        "rationale": rationale,
        "risk": risk,
        "receipts": {
            "violation_receipts": _sort_evidence_refs(violation_receipts),
            "related_edges": _sort_related_edges(related_edges),
        },
    }
    hint["hint_id"] = "hint:" + sha256_bytes(dumps_canonical(hint))
    validate(hint, "schemas/repair_hint.schema.json")
    return hint


def _policy_hints(
    violation: dict,
    events_by_id: dict[str, dict],
    related_edges: list[dict],
) -> list[dict]:
    non_policy_events = [
        event_id
        for event_id in violation["events"]
        if events_by_id[event_id]["type"] != "PolicyChange"
    ]
    target_event_ids = sorted(non_policy_events or violation["events"])
    drop_target = [target_event_ids[0]]
    return [
        _build_hint(
            violation_type=violation["type"],
            event_ids=drop_target,
            entity_ids=violation["entities"],
            action="DROP_EVENT",
            rationale=(
                "drop the source-context event that violates the policy while "
                "preserving the policy statement"
            ),
            risk="medium",
            violation_receipts=violation["evidence"],
            related_edges=related_edges,
        ),
        _build_hint(
            violation_type=violation["type"],
            event_ids=violation["events"],
            entity_ids=violation["entities"],
            action="NARROW_SCOPE",
            rationale=(
                "narrow bundle scope or query focus so the conflicting source-context "
                "evidence is excluded from this world"
            ),
            risk="low",
            violation_receipts=violation["evidence"],
            related_edges=related_edges,
        ),
    ]


def _temporal_hints(
    violation: dict,
    events_by_id: dict[str, dict],
    related_edges: list[dict],
) -> list[dict]:
    time_target = _select_time_unknown_target(violation, events_by_id)
    return [
        _build_hint(
            violation_type=violation["type"],
            event_ids=violation["events"],
            entity_ids=violation["entities"],
            action="DROP_EDGE",
            rationale=(
                "drop the temporal edge if its ordering rule is weaker than the "
                "explicit event timeline"
            ),
            risk="medium",
            violation_receipts=violation["evidence"],
            related_edges=[edge for edge in related_edges if edge["type"] == "before"],
        ),
        _build_hint(
            violation_type=violation["type"],
            event_ids=time_target,
            entity_ids=violation["entities"],
            action="MARK_TIME_UNKNOWN",
            rationale=(
                "mark one explicit event time as unknown to remove the impossible "
                "ordering constraint without deleting the event"
            ),
            risk="low",
            violation_receipts=violation["evidence"],
            related_edges=[edge for edge in related_edges if edge["type"] == "before"],
        ),
    ]


def _causal_hints(
    violation: dict,
    events_by_id: dict[str, dict],
    related_edges: list[dict],
) -> list[dict]:
    time_target = _select_time_unknown_target(violation, events_by_id)
    causal_edges = [
        edge
        for edge in related_edges
        if edge["type"] in {"causes", "enables", "mitigates"}
    ]
    return [
        _build_hint(
            violation_type=violation["type"],
            event_ids=violation["events"],
            entity_ids=violation["entities"],
            action="DROP_EDGE",
            rationale=(
                "drop the causal edge if the explicit timeline shows the effect "
                "preceding the proposed cause"
            ),
            risk="medium",
            violation_receipts=violation["evidence"],
            related_edges=causal_edges,
        ),
        _build_hint(
            violation_type=violation["type"],
            event_ids=time_target,
            entity_ids=violation["entities"],
            action="MARK_TIME_UNKNOWN",
            rationale=(
                "mark one explicit event time as unknown if the causal link is trusted "
                "more than the current timestamp"
            ),
            risk="low",
            violation_receipts=violation["evidence"],
            related_edges=causal_edges,
        ),
    ]


def _state_hints(
    violation: dict,
    related_edges: list[dict],
) -> list[dict]:
    hints = []
    if violation["entities"]:
        hints.append(
            _build_hint(
                violation_type=violation["type"],
                event_ids=violation["events"],
                entity_ids=violation["entities"],
                action="SPLIT_ENTITY",
                rationale=(
                    "split the entity if the conflicting states refer to distinct "
                    "real-world things that were merged"
                ),
                risk="medium",
                violation_receipts=violation["evidence"],
                related_edges=related_edges,
            )
        )
    hints.append(
        _build_hint(
            violation_type=violation["type"],
            event_ids=violation["events"],
            entity_ids=violation["entities"],
            action="MARK_TIME_UNKNOWN",
            rationale=(
                "mark the state event times as unknown if the contradiction is caused "
                "by over-precise timestamp alignment"
            ),
            risk="low",
            violation_receipts=violation["evidence"],
            related_edges=related_edges,
        )
    )
    return hints


def compute_repair_hints(
    constraint_report: dict,
    causal_graph: dict,
    world_model: dict,
) -> dict:
    validate(constraint_report, "schemas/constraint_report.schema.json")
    validate(causal_graph, "schemas/causal_graph.schema.json")
    validate(world_model, "schemas/world_model.schema.json")

    events_by_id = {
        event["event_id"]: event
        for event in sorted(world_model["events"], key=_event_time_sort_key)
    }

    hints = []
    for violation in sorted(constraint_report["violations"], key=_sort_key):
        related_edges = _collect_related_edges(causal_graph, violation)
        if violation["type"] == "POLICY_CONFLICT":
            hints.extend(_policy_hints(violation, events_by_id, related_edges))
        elif violation["type"] == "TEMPORAL_CONFLICT":
            hints.extend(_temporal_hints(violation, events_by_id, related_edges))
        elif violation["type"] == "CAUSAL_CONFLICT":
            hints.extend(_causal_hints(violation, events_by_id, related_edges))
        elif violation["type"] == "STATE_CONFLICT":
            hints.extend(_state_hints(violation, related_edges))

    hints = sorted(
        hints,
        key=lambda hint: (
            hint["violation_type"],
            hint["action"],
            min(hint["target"]["event_ids"], default="~"),
            min(hint["target"]["entity_ids"], default="~"),
            hint["hint_id"],
        ),
    )
    result = {
        "version": "1.0",
        "hints": hints,
    }
    validate(result, "schemas/repair_hints.schema.json")
    return result
