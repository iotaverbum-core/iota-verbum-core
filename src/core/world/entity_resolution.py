from __future__ import annotations


def resolve_entities(semantic_entities: list[dict]) -> list[dict]:
    by_name: dict[str, dict] = {}
    for entity in semantic_entities:
        key = entity["canonical_name"].strip().lower()
        target = by_name.setdefault(
            key,
            {
                "entity_id": entity["entity_id"],
                "canonical_name": entity["canonical_name"],
                "aliases": set(),
                "mentions": [],
            },
        )
        target["aliases"].add(entity["canonical_name"])
        target["mentions"].extend(entity.get("mentions", []))
    resolved = []
    for item in by_name.values():
        resolved.append(
            {
                "entity_id": item["entity_id"],
                "canonical_name": item["canonical_name"],
                "aliases": sorted(item["aliases"]),
                "mentions": sorted(
                    item["mentions"],
                    key=lambda m: (m["source_ref"]["source_id"], m["span"][0]),
                ),
            }
        )
    return sorted(resolved, key=lambda e: e["entity_id"])
