from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes, sha256_text
from core.determinism.schema_validate import validate
from core.reasoning.causal import compute_causal_graph
from core.reasoning.constraints import compute_constraints
from proposal.text_normalize import normalize_text

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^(?:[-*]|\d+\.)\s+(.*)$")
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_ALL_CAPS_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
_ISO_INSTANT_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\b")
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SECURITY_KEYWORDS = ("key", "secret", "token", "credential", "access")
_QUERY_CATEGORY_HINTS = {
    "access": {"Access", "PolicyChange"},
    "control": {"Access", "PolicyChange"},
    "credential": {"Access", "Config"},
    "secret": {"Config", "Leak", "PolicyChange"},
    "policy": {"PolicyChange"},
    "deploy": {"Deployment"},
    "deployment": {"Deployment"},
    "config": {"Config"},
    "rotation": {"Rotation"},
    "rotate": {"Rotation"},
    "leak": {"Leak"},
}


def load_world_pack(path: str) -> dict:
    pack = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(pack, "schemas/evidence_pack.schema.json")
    return pack


def _entity_id(entity_type: str, name: str, aliases: list[str]) -> str:
    return "entity:" + sha256_text(
        entity_type + "|" + name + "|" + "|".join(sorted(aliases))
    )


def _canonical_state(state: dict | None) -> str:
    return dumps_canonical(state or {}).decode("utf-8")


def _compute_world_sha256(world_obj: dict) -> str:
    world_for_hash = deepcopy(world_obj)
    world_for_hash["world_sha256"] = ""
    return sha256_bytes(dumps_canonical(world_for_hash))


def dumps_world_model(world_obj: dict) -> bytes:
    validate(world_obj, "schemas/world_model.schema.json")
    return dumps_canonical(world_obj)


def _artifact_sort_key(artifact: dict) -> tuple[str, str, int, int, str]:
    return (
        artifact["source_id"],
        artifact["chunk_id"],
        artifact["offset_start"],
        artifact["offset_end"],
        artifact["text_sha256"],
    )


def _artifact_to_source_item(artifact: dict) -> dict:
    return {
        "source_id": artifact["source_id"],
        "chunk_id": artifact["chunk_id"],
        "offset_start": artifact["offset_start"],
        "offset_end": artifact["offset_end"],
        "text_sha256": artifact["text_sha256"],
        "text": artifact["text"],
        "scope_key": _artifact_sort_key(artifact),
    }


def _source_items_from_pack(pack: dict) -> list[dict]:
    docs_by_id = {document["doc_id"]: document for document in pack["documents"]}
    ordered_chunks = sorted(
        pack["chunks"],
        key=lambda chunk: (
            docs_by_id[chunk["doc_id"]]["relpath"],
            chunk["doc_id"],
            chunk["index"],
            chunk["chunk_id"],
        ),
    )
    return [
        {
            "source_id": chunk["doc_id"],
            "chunk_id": chunk["chunk_id"],
            "offset_start": chunk["offset_start"],
            "offset_end": chunk["offset_end"],
            "text_sha256": chunk["text_sha256"],
            "text": chunk["text"],
            "scope_key": (
                docs_by_id[chunk["doc_id"]]["relpath"],
                chunk["doc_id"],
                chunk["index"],
                chunk["chunk_id"],
            ),
        }
        for chunk in ordered_chunks
    ]


def _source_items_from_artifacts(artifacts: list[dict]) -> list[dict]:
    return [
        _artifact_to_source_item(artifact)
        for artifact in sorted(artifacts, key=_artifact_sort_key)
    ]


def _iter_source_lines(source_items: list[dict]):
    for source_item in source_items:
        for line_index, raw_line in enumerate(source_item["text"].split("\n")):
            yield source_item, line_index, raw_line.strip()


def _propose_entities(source_items: list[dict]) -> list[dict]:
    entities_by_key: dict[tuple[str, str], dict] = {}
    for _source_item, _line_index, line in _iter_source_lines(source_items):
        if not line:
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            name = heading_match.group(2).strip()
            if name:
                entity_type = "Policy" if "policy" in name.lower() else "Concept"
                entities_by_key.setdefault(
                    (entity_type, name),
                    {
                        "type": entity_type,
                        "name": name,
                        "aliases": [],
                    },
                )

        for token in _BACKTICK_RE.findall(line):
            name = normalize_text(token)
            if not name:
                continue
            entities_by_key.setdefault(
                ("Secret", name),
                {
                    "type": "Secret",
                    "name": name,
                    "aliases": [],
                },
            )

        for token in _ALL_CAPS_RE.findall(line):
            name = normalize_text(token)
            if not name:
                continue
            if ("Secret", name) in entities_by_key:
                continue
            entities_by_key.setdefault(
                ("Concept", name),
                {
                    "type": "Concept",
                    "name": name,
                    "aliases": [],
                },
            )

    entities = []
    for entity in entities_by_key.values():
        aliases = sorted(
            {
                normalize_text(alias)
                for alias in entity["aliases"]
                if normalize_text(alias) and normalize_text(alias) != entity["name"]
            }
        )
        entity_obj = {
            "entity_id": _entity_id(entity["type"], entity["name"], aliases),
            "type": entity["type"],
            "name": entity["name"],
            "aliases": aliases,
        }
        validate(entity_obj, "schemas/entity.schema.json")
        entities.append(entity_obj)

    return sorted(
        entities,
        key=lambda entity: (
            entity["type"],
            entity["name"],
            entity["entity_id"],
        ),
    )


def propose_entities_from_pack(pack: dict) -> list[dict]:
    validate(pack, "schemas/evidence_pack.schema.json")
    return _propose_entities(_source_items_from_pack(pack))


def _classify_event_type(action: str) -> str:
    lower = action.lower()
    if any(term in lower for term in ["never in source", "do not commit"]):
        return "PolicyChange"
    if any(term in action for term in ["API_", "KEY", "TOKEN", "SECRET"]):
        if any(term in lower for term in ["leak", "exposed", "breach"]):
            return "Leak"
        return "Config"
    if any(term in lower for term in ["key", "secret", "token", "credential"]):
        if any(term in lower for term in ["leak", "exposed", "breach"]):
            return "Leak"
        return "Config"
    if any(term in lower for term in ["rotate", "rotation", "rotated"]):
        return "Rotation"
    if any(
        term in lower
        for term in ["deploy", "deployment", "released", "rollout"]
    ):
        return "Deployment"
    if any(
        term in lower
        for term in ["access", "login", "logged in", "credential use"]
    ):
        return "Access"
    if any(
        term in lower
        for term in [
            "leak",
            "exposed",
            "breach",
            "committed",
            "source control",
        ]
    ):
        return "Leak"
    if "policy" in lower:
        return "PolicyChange"
    if any(
        term in lower
        for term in ["config", "configure", "configured", "environment", "env-only"]
    ):
        return "Config"
    return "Other"


def _parse_time_ref(action: str) -> dict:
    instant_match = _ISO_INSTANT_RE.search(action)
    if instant_match:
        return {"kind": "instant", "value": instant_match.group(0)}

    date_match = _ISO_DATE_RE.search(action)
    if date_match:
        return {"kind": "date", "value": date_match.group(0)}

    return {"kind": "unknown"}


def _entity_tokens(entity: dict) -> list[str]:
    return [entity["name"], *entity["aliases"]]


def _extract_objects(action: str, entities: list[dict]) -> list[str]:
    action_lower = action.lower()
    object_ids = set()
    for entity in entities:
        for token in _entity_tokens(entity):
            if token.lower() in action_lower:
                object_ids.add(entity["entity_id"])
                break
    return sorted(object_ids)


def _extract_state(action: str, entities: list[dict]) -> dict | None:
    lower = action.lower()
    state = {}
    for entity in entities:
        if entity["type"] != "Secret":
            continue
        entity_name_lower = entity["name"].lower()
        if entity_name_lower not in lower:
            continue
        if "environment only" in lower or "env-only" in lower:
            state[entity["name"]] = "env-only"
        if "never in source" in lower or "never in repo" in lower:
            state[entity["name"]] = "never-in-repo"
    if not state:
        return None
    return {key: state[key] for key in sorted(state)}


def _event_id(
    event_type: str,
    time_ref: dict,
    action: str,
    actors: list[str],
    objects: list[str],
    state: dict | None,
) -> str:
    return "event:" + sha256_text(
        "|".join(
            [
                event_type,
                time_ref["kind"],
                time_ref.get("value", ""),
                action,
                "|".join(sorted(actors)),
                "|".join(sorted(objects)),
                _canonical_state(state),
            ]
        )
    )


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
    return [
        unique_refs[key]
        for key in sorted(unique_refs)
    ]


def normalize_query_tokens(query: str) -> list[str]:
    normalized = normalize_text(query).lower()
    return sorted(set(_TOKEN_RE.findall(normalized)))


def _canonical_token(token: str) -> str:
    normalized = normalize_text(token).strip()
    if not normalized:
        return ""
    return normalized.upper()


def event_tokens(event: dict) -> list[str]:
    tokens = {_canonical_token(token) for token in event["objects"]}
    state_text = ""
    if event["state"] is not None:
        state_text = " " + dumps_canonical(event["state"]).decode("utf-8")
    text = event["action"] + state_text
    for token in _BACKTICK_RE.findall(text):
        canonical = _canonical_token(token)
        if canonical:
            tokens.add(canonical)
    for token in _ALL_CAPS_RE.findall(text):
        canonical = _canonical_token(token)
        if canonical:
            tokens.add(canonical)
    for token in _TOKEN_RE.findall(normalize_text(text).lower()):
        if token:
            tokens.add(token)
    return sorted(tokens)


def _time_focus_key(event: dict) -> str:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return "~" + event["event_id"]
    return time_ref["value"]


def _implied_event_types(query_tokens: list[str]) -> set[str]:
    implied_types: set[str] = set()
    for token in query_tokens:
        implied_types.update(_QUERY_CATEGORY_HINTS.get(token, set()))
    return implied_types


def score_event(event: dict, query_tokens: list[str]) -> int:
    if not query_tokens:
        return 0

    object_token_set = {
        _canonical_token(token)
        for token in event.get("objects", [])
    }
    entity_label_tokens = {
        token.lower()
        for token in event.get("_entity_label_tokens", [])
    }
    event_token_set = {
        token.lower()
        for token in event_tokens(event)
    }
    score = 0
    for token in query_tokens:
        canonical_query = _canonical_token(token)
        if canonical_query in object_token_set:
            score += 5
        if token in event_token_set:
            score += 3
        if token in entity_label_tokens:
            score += 1
    if event["type"] in _implied_event_types(query_tokens):
        score += 2
    return score


def _is_relevant_world_line(action: str, query_tokens: list[str]) -> bool:
    action_lower = action.lower()
    if any(keyword in action_lower for keyword in _SECURITY_KEYWORDS):
        return True
    if not query_tokens:
        return True
    return any(token in action_lower for token in query_tokens)


def _propose_events(
    source_items: list[dict],
    entities: list[dict],
    *,
    query_tokens: list[str] | None = None,
) -> list[dict]:
    for entity in entities:
        validate(entity, "schemas/entity.schema.json")

    events_by_id: dict[str, dict] = {}
    effective_query_tokens = query_tokens or []
    for source_item, line_index, line in _iter_source_lines(source_items):
        if not line:
            continue
        bullet_match = _BULLET_RE.match(line)
        if bullet_match is None:
            continue

        action = normalize_text(bullet_match.group(1))
        if not action:
            continue
        if not _is_relevant_world_line(action, effective_query_tokens):
            continue

        time_ref = _parse_time_ref(action)
        objects = _extract_objects(action, entities)
        state = _extract_state(action, entities)
        event_type = _classify_event_type(action)
        evidence_ref = {
            "source_id": source_item["source_id"],
            "chunk_id": source_item["chunk_id"],
            "offset_start": source_item["offset_start"],
            "offset_end": source_item["offset_end"],
            "text_sha256": source_item["text_sha256"],
        }
        event_id = _event_id(
            event_type,
            time_ref,
            action,
            [],
            objects,
            state,
        )
        event_obj = {
            "event_id": event_id,
            "type": event_type,
            "time": time_ref,
            "actors": [],
            "objects": objects,
            "action": action,
            "state": state,
            "evidence": [evidence_ref],
            "_entity_label_tokens": sorted(
                {
                    token.lower()
                    for object_id in objects
                    for entity in entities
                    if entity["entity_id"] == object_id
                    for token in _entity_tokens(entity)
                }
            ),
            "_sort_key": (
                source_item["scope_key"],
                line_index,
                action,
                event_id,
            ),
        }
        existing = events_by_id.get(event_id)
        if existing is None:
            events_by_id[event_id] = event_obj
            continue
        existing["evidence"] = _sort_evidence_refs(
            existing["evidence"] + [evidence_ref]
        )

    events = sorted(events_by_id.values(), key=lambda event: event["_sort_key"])
    normalized_events = []
    for event in events:
        event["evidence"] = _sort_evidence_refs(event["evidence"])
        del event["_entity_label_tokens"]
        del event["_sort_key"]
        validate(event, "schemas/event.schema.json")
        normalized_events.append(event)
    return normalized_events


def propose_events_from_pack(pack: dict, entities: list[dict]) -> list[dict]:
    validate(pack, "schemas/evidence_pack.schema.json")
    return _propose_events(_source_items_from_pack(pack), entities, query_tokens=[])


def _event_sort_key(event: dict) -> tuple[int, str, str]:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return (1, "", event["event_id"])
    return (0, time_ref["value"], event["event_id"])


def _sort_json_ref(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _build_relations(events: list[dict]) -> list[dict]:
    known_events = [event for event in events if event["time"]["kind"] != "unknown"]
    known_events.sort(key=lambda event: (event["time"]["value"], event["event_id"]))
    relations = []
    for previous, current in zip(known_events, known_events[1:]):
        if previous["time"]["value"] == current["time"]["value"]:
            relation_type = "same_time"
        else:
            relation_type = "before"
        relations.append(
            {
                "from_id": previous["event_id"],
                "to_id": current["event_id"],
                "type": relation_type,
                "derived": True,
                "proof": [
                    {
                        "rule": "iso_time_order",
                        "a": previous["event_id"],
                        "b": current["event_id"],
                    }
                ],
            }
        )
    return sorted(
        relations,
        key=lambda relation: (
            relation["type"],
            relation["from_id"],
            relation["to_id"],
        ),
    )


def _build_unknowns(events: list[dict]) -> list[dict]:
    unknowns = []
    for event in events:
        if event["time"]["kind"] == "unknown":
            unknowns.append(
                {
                    "kind": "missing_time",
                    "ref": {"event_id": event["event_id"]},
                }
            )
        needs_actor_unknown = event["type"] != "Other" or any(
            keyword in event["action"].lower()
            for keyword in ["access", "secret", "key", "token", "credential"]
        )
        if not event["actors"] and needs_actor_unknown:
            unknowns.append(
                {
                    "kind": "missing_actor",
                    "ref": {"event_id": event["event_id"]},
                }
            )
        if not event["objects"]:
            unknowns.append(
                {
                    "kind": "missing_object",
                    "ref": {"event_id": event["event_id"]},
                }
            )
    return sorted(
        unknowns,
        key=lambda unknown: (unknown["kind"], _sort_json_ref(unknown["ref"])),
    )


def _build_conflicts(events: list[dict], entities: list[dict]) -> list[dict]:
    secret_ids = {
        entity["entity_id"]: entity["name"]
        for entity in entities
        if entity["type"] == "Secret"
    }
    states_by_secret: dict[str, dict[str, list[tuple[str, str]]]] = {}
    for event in events:
        if not event["state"]:
            continue
        for key, value in event["state"].items():
            for object_id in event["objects"]:
                if object_id not in secret_ids or secret_ids[object_id] != key:
                    continue
                states_by_secret.setdefault(object_id, {}).setdefault(key, []).append(
                    (str(value), event["event_id"])
                )

    conflicts = []
    for secret_id, key_groups in states_by_secret.items():
        for state_key, items in key_groups.items():
            unique_values = sorted({value for value, _event_id in items if value})
            if len(unique_values) < 2:
                continue
            related_event_ids = sorted({event_id for _value, event_id in items})
            conflicts.append(
                {
                    "kind": "state_conflict",
                    "ref": {
                        "entity_id": secret_id,
                        "event_ids": related_event_ids,
                        "key": state_key,
                        "values": unique_values,
                    },
                    "reason": (
                        f"{state_key} has conflicting states: "
                        + ", ".join(unique_values)
                    ),
                }
            )
    return sorted(
        conflicts,
        key=lambda conflict: (conflict["kind"], _sort_json_ref(conflict["ref"])),
    )


def propose_world_model(pack: dict) -> dict:
    validate(pack, "schemas/evidence_pack.schema.json")

    entities = propose_entities_from_pack(pack)
    events = propose_events_from_pack(pack, entities)
    return _build_world_model(entities, events)


def _build_world_model(entities: list[dict], events: list[dict]) -> dict:
    sorted_events = sorted(events, key=_event_sort_key)
    world_obj = {
        "world_version": "1.0",
        "world_sha256": "",
        "entities": sorted(
            entities,
            key=lambda entity: (
                entity["type"],
                entity["name"],
                entity["entity_id"],
            ),
        ),
        "events": sorted_events,
        "relations": _build_relations(sorted_events),
        "unknowns": _build_unknowns(sorted_events),
        "conflicts": _build_conflicts(sorted_events, entities),
    }
    world_obj["world_sha256"] = _compute_world_sha256(world_obj)
    validate(world_obj, "schemas/world_model.schema.json")
    return world_obj


def propose_world_model_from_artifacts(
    pack: dict,
    artifacts: list[dict],
    query: str = "",
    *,
    max_chunks: int = 10,
    max_events: int = 30,
) -> dict:
    validate(pack, "schemas/evidence_pack.schema.json")
    for artifact in artifacts:
        if sha256_text(artifact["text"]) != artifact["text_sha256"]:
            raise ValueError("artifact text_sha256 does not match artifact text")

    source_items = _source_items_from_artifacts(artifacts)
    entities = _propose_entities(source_items)
    events = _propose_events(
        source_items,
        entities,
        query_tokens=normalize_query_tokens(query),
    )
    query_tokens = normalize_query_tokens(query)
    if not query_tokens:
        return _build_world_model(entities, events)

    candidate_events = []
    entity_names_by_id = {
        entity["entity_id"]: [entity["name"], *entity["aliases"]]
        for entity in entities
    }
    for event in events:
        candidate = deepcopy(event)
        candidate["_entity_label_tokens"] = sorted(
            {
                normalize_text(label).lower()
                for object_id in event["objects"]
                for label in entity_names_by_id.get(object_id, [])
                if normalize_text(label)
            }
        )
        candidate_events.append(candidate)

    provisional_world = _build_world_model(
        entities,
        [deepcopy(event) for event in events],
    )
    provisional_causal = compute_causal_graph(provisional_world)
    provisional_constraints = compute_constraints(provisional_world, provisional_causal)

    forced_event_ids = set()
    for conflict in provisional_world["conflicts"]:
        event_ids = conflict["ref"].get("event_ids", [])
        if isinstance(event_ids, list):
            forced_event_ids.update(
                event_id
                for event_id in event_ids
                if isinstance(event_id, str)
            )
    for violation in provisional_constraints["violations"]:
        forced_event_ids.update(violation["events"])
    for finding in provisional_causal["findings"]:
        if finding["code"] == "CYCLE_TEMPORAL_CONSTRAINT":
            forced_event_ids.update(finding["event_ids"])

    k = min(max_events, max(10, max_chunks * 2))
    ranked_events = sorted(
        candidate_events,
        key=lambda event: (
            -score_event(event, query_tokens),
            _time_focus_key(event),
            event["event_id"],
        ),
    )
    selected_event_ids = {
        event["event_id"] for event in ranked_events[:k]
    }
    selected_event_ids.update(forced_event_ids)

    selected_events = [
        event
        for event in candidate_events
        if event["event_id"] in selected_event_ids
    ]
    selected_events = sorted(
        selected_events,
        key=lambda event: (
            _time_focus_key(event),
            event["event_id"],
        ),
    )
    for event in selected_events:
        del event["_entity_label_tokens"]
    return _build_world_model(entities, selected_events)
