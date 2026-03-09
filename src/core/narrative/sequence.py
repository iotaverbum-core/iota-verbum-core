from __future__ import annotations


def build_sequence(world_graph: dict) -> list[dict]:
    return sorted(
        [
            {
                "event_id": e["event_id"],
                "description": e["description"],
                "temporal_anchor": e.get("temporal_anchor"),
            }
            for e in world_graph["events"]
        ],
        key=lambda e: (e["temporal_anchor"] or "", e["event_id"]),
    )
