from __future__ import annotations

from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate
from core.world.entity_resolution import resolve_entities
from core.world.event_normalization import normalize_events
from core.world.versioning import next_version


def build_world_graph(semantic: dict, previous_version: str | None = None) -> dict:
    entities = resolve_entities(semantic["entities"])
    events = normalize_events(semantic["events"])
    unknowns = []
    for event in events:
        if event.get("temporal_anchor") is None:
            unknowns.append(
                {
                    "kind": "missing_temporal_anchor",
                    "ref": {"event_id": event["event_id"]},
                }
            )
    world = {
        "schema_version": "2.0",
        "graph_version": next_version(previous_version),
        "entities": entities,
        "events": events,
        "relations": semantic["relations"],
        "claims": semantic["claims"],
        "unknowns": sorted(unknowns, key=lambda i: i["ref"]["event_id"]),
        "conflicts": [],
    }
    from core.determinism.canonical_json import dumps_canonical

    world_hash = sha256_bytes(dumps_canonical(world))
    world["graph_sha256"] = world_hash
    validate(world, "schemas/world_graph_v2.schema.json")
    return world
