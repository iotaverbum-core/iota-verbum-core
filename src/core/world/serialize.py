from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical


def serialize_world_graph(world_graph: dict) -> bytes:
    return dumps_canonical(world_graph)
