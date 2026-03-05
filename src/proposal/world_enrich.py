from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.schema_validate import validate
from proposal.text_normalize import normalize_text
from proposal.world_propose import (
    _build_conflicts,
    _build_relations,
    _build_unknowns,
    _compute_world_sha256,
)


def _sort_json_ref(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _normalize_time(time_ref: dict) -> dict:
    kind = time_ref["kind"]
    if kind == "unknown":
        normalized = {"kind": "unknown"}
    elif kind == "date":
        normalized = {"kind": "date", "value": normalize_text(time_ref["value"])}
    elif kind == "datetime":
        normalized = {"kind": "instant", "value": normalize_text(time_ref["value"])}
    elif kind == "relative":
        normalized = {"kind": "unknown"}
    else:
        raise ValueError(f"unsupported enrichment time kind: {kind}")
    validate(normalized, "schemas/time_ref.schema.json")
    return normalized


def _normalize_enrichment(enrichment: dict) -> dict:
    normalized_events = []
    seen_event_ids: set[str] = set()
    for item in enrichment["events"]:
        event_id = item["event_id"]
        if event_id in seen_event_ids:
            raise ValueError(f"duplicate enrichment event_id: {event_id}")
        seen_event_ids.add(event_id)
        normalized_item = {"event_id": event_id}
        if "actors" in item:
            actor_values = {
                normalize_text(actor)
                for actor in item["actors"]
                if normalize_text(actor)
            }
            normalized_item["actors"] = sorted(
                actor_values
            )
            if not normalized_item["actors"]:
                raise ValueError(
                    f"enrichment actors empty after normalization: {event_id}"
                )
        if "objects" in item:
            object_values = {
                normalize_text(object_id)
                for object_id in item["objects"]
                if normalize_text(object_id)
            }
            normalized_item["objects"] = sorted(
                object_values
            )
            if not normalized_item["objects"]:
                raise ValueError(
                    f"enrichment objects empty after normalization: {event_id}"
                )
        if "time" in item:
            normalized_item["time"] = _normalize_time(item["time"])
        normalized_events.append(normalized_item)

    normalized = {
        "version": "1.0",
        "events": sorted(normalized_events, key=lambda item: item["event_id"]),
    }
    validate(normalized, "schemas/world_enrichment.schema.json")
    return normalized


def load_world_enrichment(path: str | Path) -> dict:
    raw_text = Path(path).read_text(encoding="utf-8")
    normalized_text = normalize_text(raw_text)
    enrichment = json.loads(normalized_text)
    validate(enrichment, "schemas/world_enrichment.schema.json")
    return _normalize_enrichment(enrichment)


def _event_sort_key(event: dict) -> tuple[int, str, str]:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return (1, "", event["event_id"])
    return (0, time_ref["value"], event["event_id"])


def _conflict_sort_key(conflict: dict) -> tuple[str, str]:
    return (conflict["kind"], _sort_json_ref(conflict["ref"]))


def apply_world_enrichment(world_model: dict, enrichment: dict) -> dict:
    validate(world_model, "schemas/world_model.schema.json")
    validate(enrichment, "schemas/world_enrichment.schema.json")
    enrichment = _normalize_enrichment(enrichment)

    enriched_world = deepcopy(world_model)
    enrichment_by_event_id = {
        item["event_id"]: item for item in enrichment["events"]
    }
    enriched_events = []
    time_conflicts = []

    for event in enriched_world["events"]:
        patch = enrichment_by_event_id.get(event["event_id"])
        if patch is None:
            enriched_events.append(event)
            continue

        updated_event = deepcopy(event)
        if "actors" in patch:
            updated_event["actors"] = sorted(
                set(updated_event["actors"]) | set(patch["actors"])
            )
        if "objects" in patch:
            updated_event["objects"] = sorted(
                set(updated_event["objects"]) | set(patch["objects"])
            )
        if "time" in patch:
            existing_time = updated_event["time"]
            enrichment_time = patch["time"]
            if existing_time["kind"] == "unknown":
                updated_event["time"] = enrichment_time
            elif dumps_canonical(existing_time) != dumps_canonical(enrichment_time):
                time_conflicts.append(
                    {
                        "kind": "ordering_conflict",
                        "ref": {
                            "event_id": updated_event["event_id"],
                            "source": "world_enrichment",
                            "existing_time": existing_time,
                            "enrichment_time": enrichment_time,
                        },
                        "reason": "enrichment time conflicts with existing event time",
                    }
                )
        enriched_events.append(updated_event)

    enriched_world["events"] = enriched_events
    enriched_world["relations"] = _build_relations(enriched_events)
    enriched_world["unknowns"] = _build_unknowns(enriched_events)
    enriched_world["conflicts"] = sorted(
        _build_conflicts(enriched_events, enriched_world["entities"]) + time_conflicts,
        key=_conflict_sort_key,
    )
    enriched_world["world_sha256"] = _compute_world_sha256(enriched_world)
    validate(enriched_world, "schemas/world_model.schema.json")
    return enriched_world
