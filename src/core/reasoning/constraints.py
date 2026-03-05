from __future__ import annotations

from collections import defaultdict

from core.determinism.canonical_json import dumps_canonical
from core.determinism.schema_validate import validate

_POLICY_NEVER_SOURCE_TERMS = (
    "must never appear in source",
    "must never be in source",
    "must never in source",
    "must never appear in repo",
    "must never be in repo",
    "must be never in source",
    "never in source",
)
_SOURCE_CONTEXT_TERMS = (
    "source",
    "repo",
    "repository",
    "commit",
    "committed",
)
_STATE_NEGATIONS = {
    "active": "destroyed",
    "destroyed": "active",
    "enabled": "disabled",
    "disabled": "enabled",
}


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


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


def _time_sort_key(event: dict) -> tuple[int, str, str]:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return (1, "", event["event_id"])
    return (0, time_ref["value"], event["event_id"])


def _time_value(event: dict) -> str | None:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return None
    return time_ref["value"]


def _build_violation(
    *,
    violation_type: str,
    events: list[str],
    entities: list[str],
    reason: str,
    evidence: list[dict],
) -> dict:
    violation = {
        "type": violation_type,
        "events": sorted(events),
        "entities": sorted(entities),
        "reason": reason,
        "evidence": _sort_evidence_refs(evidence),
    }
    validate(violation, "schemas/constraint_violation.schema.json")
    return violation


def _policy_conflicts(events: list[dict]) -> list[dict]:
    policy_events = [
        event
        for event in events
        if event["type"] == "PolicyChange"
        and any(term in event["action"].lower() for term in _POLICY_NEVER_SOURCE_TERMS)
    ]
    violations = []
    for policy_event in sorted(policy_events, key=_time_sort_key):
        protected_objects = sorted(policy_event["objects"])
        for event in events:
            if event["event_id"] == policy_event["event_id"]:
                continue
            if not set(protected_objects).intersection(event["objects"]):
                continue
            action_lower = event["action"].lower()
            if not any(term in action_lower for term in _SOURCE_CONTEXT_TERMS):
                continue
            violations.append(
                _build_violation(
                    violation_type="POLICY_CONFLICT",
                    events=[policy_event["event_id"], event["event_id"]],
                    entities=sorted(set(protected_objects).intersection(event["objects"])),
                    reason=(
                        "policy forbids source exposure for the same object referenced "
                        "in a source-context event"
                    ),
                    evidence=policy_event["evidence"] + event["evidence"],
                )
            )
    return violations


def _temporal_conflicts(
    events_by_id: dict[str, dict],
    causal_graph: dict,
) -> list[dict]:
    violations = []
    for edge in sorted(causal_graph["edges"], key=_sort_key):
        if edge["type"] != "before":
            continue
        from_event = events_by_id[edge["from_event_id"]]
        to_event = events_by_id[edge["to_event_id"]]
        from_time = _time_value(from_event)
        to_time = _time_value(to_event)
        if from_time is None or to_time is None or to_time >= from_time:
            continue
        violations.append(
            _build_violation(
                violation_type="TEMPORAL_CONFLICT",
                events=[from_event["event_id"], to_event["event_id"]],
                entities=sorted(set(from_event["objects"]).intersection(to_event["objects"])),
                reason=(
                    "causal before edge conflicts with explicit timeline ordering"
                ),
                evidence=edge["evidence"],
            )
        )
    return violations


def _causal_conflicts(events_by_id: dict[str, dict], causal_graph: dict) -> list[dict]:
    violations = []
    for edge in sorted(causal_graph["edges"], key=_sort_key):
        if edge["type"] != "causes":
            continue
        from_event = events_by_id[edge["from_event_id"]]
        to_event = events_by_id[edge["to_event_id"]]
        from_time = _time_value(from_event)
        to_time = _time_value(to_event)
        if from_time is None or to_time is None or to_time >= from_time:
            continue
        violations.append(
            _build_violation(
                violation_type="CAUSAL_CONFLICT",
                events=[from_event["event_id"], to_event["event_id"]],
                entities=sorted(set(from_event["objects"]).intersection(to_event["objects"])),
                reason="causal edge points to an event that occurs earlier in time",
                evidence=edge["evidence"],
            )
        )
    return violations


def _state_conflicts(events: list[dict]) -> list[dict]:
    states_by_key: dict[
        tuple[str, str, str],
        list[tuple[str, dict]],
    ] = defaultdict(list)
    for event in events:
        time_value = _time_value(event)
        if time_value is None or event["state"] is None:
            continue
        for object_id in sorted(event["objects"]):
            for state_key, state_value in sorted(event["state"].items()):
                states_by_key[(object_id, time_value, state_key)].append(
                    (str(state_value), event)
                )

    violations = []
    for (
        entity_id,
        time_value,
        state_key,
    ), state_items in sorted(states_by_key.items()):
        values = sorted({value for value, _event in state_items})
        if len(values) < 2:
            continue
        contradictory = False
        for value in values:
            if _STATE_NEGATIONS.get(value) in values:
                contradictory = True
                break
        if not contradictory:
            continue
        related_events = sorted({event["event_id"] for _value, event in state_items})
        evidence = []
        for _value, event in state_items:
            evidence.extend(event["evidence"])
        violations.append(
            _build_violation(
                violation_type="STATE_CONFLICT",
                events=related_events,
                entities=[entity_id],
                reason=(
                    f"entity has contradictory state values for {state_key} at "
                    f"{time_value}: {', '.join(values)}"
                ),
                evidence=evidence,
            )
        )
    return violations


def compute_constraints(world_model: dict, causal_graph: dict) -> dict:
    validate(world_model, "schemas/world_model.schema.json")
    validate(causal_graph, "schemas/causal_graph.schema.json")

    events = sorted(world_model["events"], key=_time_sort_key)
    events_by_id = {event["event_id"]: event for event in events}
    violations = (
        _policy_conflicts(events)
        + _temporal_conflicts(events_by_id, causal_graph)
        + _causal_conflicts(events_by_id, causal_graph)
        + _state_conflicts(events)
    )
    violations = sorted(
        violations,
        key=lambda item: (
            item["type"],
            tuple(item["events"]),
            tuple(item["entities"]),
            item["reason"],
            _sort_key({"evidence": item["evidence"]}),
        ),
    )
    report = {
        "version": "1.0",
        "violations": violations,
        "counts": {
            "policy": sum(
                1 for item in violations if item["type"] == "POLICY_CONFLICT"
            ),
            "temporal": sum(
                1 for item in violations if item["type"] == "TEMPORAL_CONFLICT"
            ),
            "causal": sum(
                1 for item in violations if item["type"] == "CAUSAL_CONFLICT"
            ),
            "state": sum(
                1 for item in violations if item["type"] == "STATE_CONFLICT"
            ),
        },
    }
    validate(report, "schemas/constraint_report.schema.json")
    return report
