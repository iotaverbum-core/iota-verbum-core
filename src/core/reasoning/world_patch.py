from __future__ import annotations

import json
import unicodedata
from copy import deepcopy
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.finalize import finalize
from core.determinism.hashing import sha256_bytes
from core.determinism.ledger import write_run
from core.determinism.schema_validate import validate
from core.reasoning.causal import compute_causal_graph
from core.reasoning.causal_narrative_v2 import render_causal_narrative_v2
from core.reasoning.constraint_diff import compute_constraint_diff
from core.reasoning.constraint_diff_narrative_v2 import (
    render_constraint_diff_narrative_v2,
)
from core.reasoning.constraint_narrative_v2 import render_constraint_narrative_v2
from core.reasoning.constraints import compute_constraints
from core.reasoning.counterfactual import load_base_output
from core.reasoning.critical_path import compute_critical_path
from core.reasoning.critical_path_narrative_v2 import (
    render_critical_path_narrative_v2,
)
from core.reasoning.repair_hints import compute_repair_hints
from core.reasoning.repair_hints_narrative_v2 import (
    render_repair_hints_narrative_v2,
)
from core.reasoning.verifier import verify_claim
from core.reasoning.world_diff import compute_world_diff
from core.reasoning.world_diff_narrative import render_world_diff_narrative
from core.reasoning.world_narrative_v2 import render_world_narrative_v2
from core.reasoning.world_patch_narrative_v2 import render_world_patch_narrative_v2

_ENTITY_TYPES = {"Person", "Org", "System", "Secret", "Policy", "Service", "Concept"}
_EVENT_TYPES = {
    "Config",
    "Access",
    "Leak",
    "Rotation",
    "Deployment",
    "PolicyChange",
    "Other",
}
_RELATION_TYPES = {"before", "after", "same_time"}
_ENTITY_UPDATE_FIELDS = {"name", "type", "aliases"}
_EVENT_UPDATE_FIELDS = {
    "type",
    "time",
    "actors",
    "objects",
    "action",
    "state",
    "evidence",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _manifest_sha256() -> str:
    return sha256_bytes((_repo_root() / "MANIFEST.sha256").read_bytes())


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def _write_or_verify(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"existing world patch file mismatch: {path}")
        return
    _write_atomic(path, data)


def _dir_matches_planned(run_dir: Path, planned_files: dict[str, bytes]) -> bool:
    for relpath, data in planned_files.items():
        path = run_dir / relpath
        if path.exists() and path.read_bytes() != data:
            return False
    return True


def _resolve_run_dir(base_run_dir: Path, planned_files: dict[str, bytes]) -> Path:
    if _dir_matches_planned(base_run_dir, planned_files):
        return base_run_dir
    conflict_index = 1
    while True:
        candidate = base_run_dir.parent / (
            f"{base_run_dir.name}__conflict_{conflict_index}"
        )
        if _dir_matches_planned(candidate, planned_files):
            return candidate
        conflict_index += 1


def _normalize_text_input(raw: bytes) -> str:
    text = raw.decode("utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text)


def _patch_for_hash(patch: dict) -> dict:
    hashed = deepcopy(patch)
    hashed["patch_id"] = ""
    for op in hashed.get("ops", []):
        op["op_id"] = ""
        op.setdefault("receipts", {})
        op["receipts"]["patch_sha256"] = ""
        op["receipts"].setdefault("evidence_refs", [])
    return hashed


def _build_patch_with_ids(raw_patch: dict) -> tuple[dict, str]:
    normalized = deepcopy(raw_patch)
    normalized.setdefault("patch_id", "")
    for op in normalized.get("ops", []):
        op.setdefault("op_id", "")
        op.setdefault("receipts", {})
        op["receipts"].setdefault("patch_sha256", "")
        op["receipts"].setdefault("evidence_refs", [])

    patch_sha256 = sha256_bytes(dumps_canonical(_patch_for_hash(normalized)))
    expected_patch_id = f"patch:{patch_sha256}"
    provided_patch_id = str(normalized.get("patch_id", ""))
    if provided_patch_id and provided_patch_id != expected_patch_id:
        raise ValueError(
            "world patch patch_id does not match canonical patch hash; "
            f"expected patch_id={expected_patch_id}"
        )
    normalized["patch_id"] = expected_patch_id

    for op in normalized["ops"]:
        provided_patch_sha = str(op["receipts"].get("patch_sha256", ""))
        if provided_patch_sha and provided_patch_sha != patch_sha256:
            raise ValueError(
                "world patch op receipt patch_sha256 does not match patch hash; "
                f"expected patch_sha256={patch_sha256}"
            )
        op["receipts"]["patch_sha256"] = patch_sha256
        op_hash_obj = deepcopy(op)
        op_hash_obj["op_id"] = ""
        expected_op_id = "op:" + sha256_bytes(dumps_canonical(op_hash_obj))
        provided_op_id = str(op.get("op_id", ""))
        if provided_op_id and provided_op_id != expected_op_id:
            raise ValueError(
                "world patch op_id does not match canonical op hash; "
                f"expected op_id={expected_op_id}"
            )
        op["op_id"] = expected_op_id

    validate(normalized, "schemas/world_patch.schema.json")
    return normalized, patch_sha256


def load_world_patch(path: str) -> tuple[dict, bytes, str]:
    raw_bytes = Path(path).read_bytes()
    raw_obj = json.loads(_normalize_text_input(raw_bytes))
    patch_obj, patch_sha256 = _build_patch_with_ids(raw_obj)
    patch_bytes = dumps_canonical(patch_obj)
    validate(patch_obj, "schemas/world_patch.schema.json")
    return patch_obj, patch_bytes, patch_sha256


def _event_time_key(event: dict) -> tuple[int, str, str]:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return (1, "", event["event_id"])
    return (0, time_ref["value"], event["event_id"])


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
    return sorted(unknowns, key=lambda item: (item["kind"], _sort_key(item["ref"])))


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
        key=lambda conflict: (conflict["kind"], _sort_key(conflict["ref"])),
    )


def _compute_world_sha256(world_obj: dict) -> str:
    hashed = deepcopy(world_obj)
    hashed["world_sha256"] = ""
    return sha256_bytes(dumps_canonical(hashed))


def _normalize_world_model(world_model: dict) -> dict:
    entities = sorted(
        [deepcopy(entity) for entity in world_model["entities"]],
        key=lambda entity: entity["entity_id"],
    )
    events = sorted(
        [deepcopy(event) for event in world_model["events"]],
        key=_event_time_key,
    )
    relations = sorted(
        [deepcopy(relation) for relation in world_model["relations"]],
        key=lambda relation: (
            relation["type"],
            relation["from_id"],
            relation["to_id"],
            1 if relation.get("derived", False) else 0,
            _sort_key({"proof": relation.get("proof")}),
        ),
    )
    normalized = {
        "world_version": "1.0",
        "world_sha256": "",
        "entities": entities,
        "events": events,
        "relations": relations,
        "unknowns": _build_unknowns(events),
        "conflicts": _build_conflicts(events, entities),
    }
    normalized["world_sha256"] = _compute_world_sha256(normalized)
    validate(normalized, "schemas/world_model.schema.json")
    return normalized


def _require_payload(op: dict) -> dict:
    payload = op.get("payload")
    if not isinstance(payload, dict):
        raise ValueError(f"missing payload for {op['op']}")
    return payload


def _validate_entity_payload(payload: dict) -> None:
    required = {"entity_id", "type", "name", "aliases"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"ADD_ENTITY payload missing fields: {', '.join(missing)}")
    if payload["type"] not in _ENTITY_TYPES:
        raise ValueError(f"invalid entity type: {payload['type']}")


def _validate_event_payload(payload: dict) -> None:
    required = {
        "event_id",
        "type",
        "time",
        "actors",
        "objects",
        "action",
        "state",
        "evidence",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"ADD_EVENT payload missing fields: {', '.join(missing)}")
    if payload["type"] not in _EVENT_TYPES:
        raise ValueError(f"invalid event type: {payload['type']}")


def _all_world_ids(world_model: dict) -> set[str]:
    ids = {entity["entity_id"] for entity in world_model["entities"]}
    ids.update(event["event_id"] for event in world_model["events"])
    return ids


def apply_world_patch(world_model: dict, patch_obj: dict) -> dict:
    validate(world_model, "schemas/world_model.schema.json")
    validate(patch_obj, "schemas/world_patch.schema.json")
    updated = deepcopy(world_model)

    for op in patch_obj["ops"]:
        op_type = op["op"]
        target = op["target"]

        if op_type == "ADD_ENTITY":
            payload = _require_payload(op)
            _validate_entity_payload(payload)
            entity_id = payload["entity_id"]
            if entity_id in {item["entity_id"] for item in updated["entities"]}:
                raise ValueError(f"ADD_ENTITY target already exists: {entity_id}")
            updated["entities"].append(
                {
                    "entity_id": entity_id,
                    "type": payload["type"],
                    "name": payload["name"],
                    "aliases": sorted(payload["aliases"]),
                }
            )
            continue

        if op_type == "UPDATE_ENTITY":
            payload = _require_payload(op)
            unsupported = sorted(set(payload) - _ENTITY_UPDATE_FIELDS)
            if unsupported:
                raise ValueError(
                    "UPDATE_ENTITY contains unsupported fields: "
                    + ", ".join(unsupported)
                )
            entity_id = target.get("entity_id", "")
            entity = next(
                (
                    item
                    for item in updated["entities"]
                    if item["entity_id"] == entity_id
                ),
                None,
            )
            if entity is None:
                raise ValueError(f"UPDATE_ENTITY target not found: {entity_id}")
            if "type" in payload and payload["type"] not in _ENTITY_TYPES:
                raise ValueError(f"invalid entity type: {payload['type']}")
            for field in _ENTITY_UPDATE_FIELDS:
                if field in payload:
                    entity[field] = deepcopy(payload[field])
            if "aliases" in payload:
                entity["aliases"] = sorted(entity["aliases"])
            continue

        if op_type == "REMOVE_ENTITY":
            entity_id = target.get("entity_id", "")
            if entity_id not in {item["entity_id"] for item in updated["entities"]}:
                raise ValueError(f"REMOVE_ENTITY target not found: {entity_id}")
            referenced_by_events = [
                event["event_id"]
                for event in updated["events"]
                if entity_id in event["actors"] or entity_id in event["objects"]
            ]
            if referenced_by_events:
                raise ValueError(
                    "REMOVE_ENTITY blocked; entity referenced by events: "
                    + ", ".join(sorted(referenced_by_events))
                )
            referenced_by_relations = [
                relation
                for relation in updated["relations"]
                if relation["from_id"] == entity_id or relation["to_id"] == entity_id
            ]
            if referenced_by_relations:
                raise ValueError(
                    "REMOVE_ENTITY blocked; entity referenced by relations: "
                    + ", ".join(
                        sorted(
                            f"{item['type']}:{item['from_id']}->{item['to_id']}"
                            for item in referenced_by_relations
                        )
                    )
                )
            updated["entities"] = [
                item for item in updated["entities"] if item["entity_id"] != entity_id
            ]
            continue

        if op_type == "ADD_EVENT":
            payload = _require_payload(op)
            _validate_event_payload(payload)
            event_id = payload["event_id"]
            if event_id in {item["event_id"] for item in updated["events"]}:
                raise ValueError(f"ADD_EVENT target already exists: {event_id}")
            updated["events"].append(
                {
                    "event_id": event_id,
                    "type": payload["type"],
                    "time": deepcopy(payload["time"]),
                    "actors": sorted(payload["actors"]),
                    "objects": sorted(payload["objects"]),
                    "action": payload["action"],
                    "state": deepcopy(payload["state"]),
                    "evidence": sorted(payload["evidence"], key=_sort_key),
                }
            )
            continue

        if op_type == "UPDATE_EVENT":
            payload = _require_payload(op)
            unsupported = sorted(set(payload) - _EVENT_UPDATE_FIELDS)
            if unsupported:
                raise ValueError(
                    "UPDATE_EVENT contains unsupported fields: "
                    + ", ".join(unsupported)
                )
            event_id = target.get("event_id", "")
            event = next(
                (item for item in updated["events"] if item["event_id"] == event_id),
                None,
            )
            if event is None:
                raise ValueError(f"UPDATE_EVENT target not found: {event_id}")
            if "type" in payload and payload["type"] not in _EVENT_TYPES:
                raise ValueError(f"invalid event type: {payload['type']}")
            for field in _EVENT_UPDATE_FIELDS:
                if field in payload:
                    event[field] = deepcopy(payload[field])
            if "actors" in payload:
                event["actors"] = sorted(event["actors"])
            if "objects" in payload:
                event["objects"] = sorted(event["objects"])
            if "evidence" in payload:
                event["evidence"] = sorted(event["evidence"], key=_sort_key)
            continue

        if op_type == "REMOVE_EVENT":
            event_id = target.get("event_id", "")
            if event_id not in {item["event_id"] for item in updated["events"]}:
                raise ValueError(f"REMOVE_EVENT target not found: {event_id}")
            updated["events"] = [
                item for item in updated["events"] if item["event_id"] != event_id
            ]
            updated["relations"] = [
                relation
                for relation in updated["relations"]
                if relation["from_id"] != event_id and relation["to_id"] != event_id
            ]
            continue

        if op_type == "ADD_RELATION":
            payload = _require_payload(op)
            relation_key = target.get("relation_key", {})
            required_fields = {"from_id", "to_id", "type", "derived", "proof"}
            missing = sorted(required_fields - set(payload))
            if missing:
                raise ValueError(
                    f"ADD_RELATION payload missing fields: {', '.join(missing)}"
                )
            if payload["type"] not in _RELATION_TYPES:
                raise ValueError(f"invalid relation type: {payload['type']}")
            if relation_key:
                if (
                    relation_key.get("from_id") != payload["from_id"]
                    or relation_key.get("to_id") != payload["to_id"]
                    or relation_key.get("type") != payload["type"]
                ):
                    raise ValueError(
                        "ADD_RELATION target.relation_key does not match payload"
                    )
            world_ids = _all_world_ids(updated)
            if payload["from_id"] not in world_ids or payload["to_id"] not in world_ids:
                raise ValueError(
                    "ADD_RELATION references unknown id(s): "
                    f"{payload['from_id']} -> {payload['to_id']}"
                )
            relation_obj = {
                "from_id": payload["from_id"],
                "to_id": payload["to_id"],
                "type": payload["type"],
                "derived": bool(payload["derived"]),
                "proof": deepcopy(payload["proof"]),
            }
            if any(
                _sort_key(item) == _sort_key(relation_obj)
                for item in updated["relations"]
            ):
                raise ValueError(
                    "ADD_RELATION target already exists: "
                    f"{payload['type']}:{payload['from_id']}->{payload['to_id']}"
                )
            updated["relations"].append(relation_obj)
            continue

        if op_type == "REMOVE_RELATION":
            relation_key = target.get("relation_key", {})
            relation_type = relation_key.get("type", "")
            from_id = relation_key.get("from_id", "")
            to_id = relation_key.get("to_id", "")
            if relation_type not in _RELATION_TYPES:
                raise ValueError(f"invalid relation type: {relation_type}")
            before_len = len(updated["relations"])
            updated["relations"] = [
                relation
                for relation in updated["relations"]
                if not (
                    relation["type"] == relation_type
                    and relation["from_id"] == from_id
                    and relation["to_id"] == to_id
                )
            ]
            if len(updated["relations"]) == before_len:
                raise ValueError(
                    "REMOVE_RELATION target not found: "
                    f"{relation_type}:{from_id}->{to_id}"
                )
            continue

        raise ValueError(f"unsupported world patch op: {op_type}")

    return _normalize_world_model(updated)


def _sealed_output_wrapper(
    output_obj: dict,
    *,
    output_sha256: str,
    attestation_sha256: str,
) -> dict:
    return {
        "output": output_obj,
        "__meta__": {
            "output_sha256": output_sha256,
            "attestation_sha256": attestation_sha256,
        },
    }


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(_repo_root().resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def build_patched_output(
    base_output: dict,
    patched_world_model: dict,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    manifest_sha256: str,
    ledger_root: str,
    *,
    patch_obj: dict,
    mode: str,
    max_lines: int,
) -> dict:
    causal_graph = compute_causal_graph(patched_world_model)
    critical_path = compute_critical_path(causal_graph)
    constraint_report = compute_constraints(patched_world_model, causal_graph)
    repair_hints = compute_repair_hints(
        constraint_report, causal_graph, patched_world_model
    )
    target_claim_id = base_output["output_obj"]["verification_result"][
        "target_claim_id"
    ]
    output_obj = {
        "world_model": patched_world_model,
        "world_patch": deepcopy(patch_obj),
        "causal_graph": causal_graph,
        "causal_findings": causal_graph["findings"],
        "critical_path": critical_path,
        "constraint_report": constraint_report,
        "repair_hints": repair_hints,
    }
    verification_result = verify_claim(
        ruleset_id=ruleset_id,
        target_claim_id=target_claim_id,
        evidence_bundle_obj=base_output["bundle_obj"],
        sealed_output_obj=output_obj,
    )
    output_obj["world_narrative_v2"] = render_world_narrative_v2(
        world_model=patched_world_model,
        verification_result=verification_result,
        mode=mode,
        max_lines=max_lines,
    )
    output_obj["causal_narrative_v2"] = render_causal_narrative_v2(
        causal_graph,
        verification_result=verification_result,
        max_lines=max_lines,
        verbosity=mode,
    )
    output_obj["critical_path_narrative_v2"] = render_critical_path_narrative_v2(
        critical_path,
        mode=mode,
        max_lines=max_lines,
    )
    output_obj["constraint_narrative_v2"] = render_constraint_narrative_v2(
        constraint_report,
        mode=mode,
        max_lines=max_lines,
    )
    output_obj["repair_hints_narrative_v2"] = render_repair_hints_narrative_v2(
        repair_hints,
        max_lines=max_lines,
        verbosity=mode,
    )
    output_obj["verification_result"] = verification_result
    sealed = finalize(
        base_output["bundle_obj"],
        output_obj,
        manifest_sha256=manifest_sha256,
        core_version=core_version,
        ruleset_id=ruleset_id,
        created_utc=created_utc,
    )
    ledger_dir = write_run(ledger_root=ledger_root, **sealed)
    return {
        "output_obj": output_obj,
        "sealed": sealed,
        "ledger_dir": str(ledger_dir.resolve().as_posix()),
    }


def run_world_patch(
    *,
    base: str,
    patch: str,
    out_dir: str,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    with_diff: bool = True,
    with_constraint_diff: bool = True,
    mode: str = "brief",
    max_lines: int = 200,
) -> dict:
    base_path = Path(base).resolve()
    source_kind = "ledger_dir" if base_path.is_dir() else "output_json"
    base_loaded = load_base_output(
        {"kind": source_kind, "path": str(base_path.as_posix())}
    )
    base_output_obj = base_loaded["output_obj"]
    if (
        "world_model" not in base_output_obj
        or "verification_result" not in base_output_obj
    ):
        raise ValueError("base output missing world_model or verification_result")

    patch_obj, patch_bytes, patch_sha256 = load_world_patch(patch)
    patch_base_kind = patch_obj["base_ref"]["kind"]
    if patch_base_kind != source_kind:
        raise ValueError(
            "world patch base_ref.kind mismatch; "
            f"expected {source_kind}, got {patch_base_kind}"
        )
    patch_base_value = Path(patch_obj["base_ref"]["value"]).resolve().as_posix()
    if patch_base_value != base_path.as_posix():
        raise ValueError(
            f"world patch base_ref.value mismatch; expected {base_path.as_posix()}"
        )

    patched_world = apply_world_patch(base_output_obj["world_model"], patch_obj)

    run_root = Path(out_dir)
    run_dir_name = f"patch_{patch_sha256}"
    base_run_dir = run_root / run_dir_name
    run_dir = _resolve_run_dir(base_run_dir, {"patch.json": patch_bytes})

    built = build_patched_output(
        base_loaded,
        patched_world,
        created_utc,
        core_version,
        ruleset_id,
        _manifest_sha256(),
        str((run_dir / "ledger").as_posix()),
        patch_obj=patch_obj,
        mode=mode,
        max_lines=max_lines,
    )
    sealed = built["sealed"]

    world_diff = None
    world_diff_narrative = None
    if with_diff:
        world_diff = compute_world_diff(
            old_output=_sealed_output_wrapper(
                base_output_obj,
                output_sha256=base_loaded["output_sha256"],
                attestation_sha256=base_loaded["attestation_sha256"],
            ),
            new_output=_sealed_output_wrapper(
                built["output_obj"],
                output_sha256=sealed["output_sha256"],
                attestation_sha256=sealed["attestation_sha256"],
            ),
        )
        world_diff_narrative = render_world_diff_narrative(
            world_diff,
            mode=mode,
            max_lines=max_lines,
        )

    constraint_diff = None
    constraint_diff_narrative = None
    if with_constraint_diff:
        base_for_constraint = deepcopy(base_output_obj)
        if "constraint_report" not in base_for_constraint:
            if "causal_graph" not in base_for_constraint:
                base_for_constraint["causal_graph"] = compute_causal_graph(
                    base_for_constraint["world_model"]
                )
            base_for_constraint["constraint_report"] = compute_constraints(
                base_for_constraint["world_model"],
                base_for_constraint["causal_graph"],
            )
        constraint_diff = compute_constraint_diff(
            old_output=_sealed_output_wrapper(
                base_for_constraint,
                output_sha256=base_loaded["output_sha256"],
                attestation_sha256=base_loaded["attestation_sha256"],
            ),
            new_output=_sealed_output_wrapper(
                built["output_obj"],
                output_sha256=sealed["output_sha256"],
                attestation_sha256=sealed["attestation_sha256"],
            ),
        )
        constraint_diff_narrative = render_constraint_diff_narrative_v2(
            constraint_diff,
            mode=mode,
            max_lines=max_lines,
        )

    patch_result = {
        "version": "1.0",
        "patch_id": patch_obj["patch_id"],
        "base": {
            "world_sha256": base_output_obj["world_model"]["world_sha256"],
            "output_sha256": base_loaded["output_sha256"],
            "attestation_sha256": base_loaded["attestation_sha256"],
        },
        "new": {
            "world_sha256": built["output_obj"]["world_model"]["world_sha256"],
            "output_sha256": sealed["output_sha256"],
            "attestation_sha256": sealed["attestation_sha256"],
        },
        "verification_change": {
            "old": base_output_obj["verification_result"]["status"],
            "new": built["output_obj"]["verification_result"]["status"],
        },
        "ledger_dir": _repo_relative(Path(built["ledger_dir"])),
        "receipts": {
            "patch_sha256": patch_sha256,
            "op_count": len(patch_obj["ops"]),
        },
    }
    if world_diff is not None:
        patch_result["world_diff"] = world_diff
    if constraint_diff is not None:
        patch_result["constraint_diff"] = constraint_diff
    validate(patch_result, "schemas/world_patch_result.schema.json")

    narrative_obj = render_world_patch_narrative_v2(
        patch_obj,
        patch_result,
        mode=mode,
        max_lines=max_lines,
    )
    validate(narrative_obj, "schemas/world_patch_narrative_v2.schema.json")

    planned_files = {
        "patch.json": patch_bytes,
        "output.json": sealed["output_bytes"],
        "attestation.json": sealed["attestation_bytes"],
        "world_patch_result.json": dumps_canonical(patch_result),
        "world_patch_narrative_v2.json": dumps_canonical(narrative_obj),
        "world_patch_narrative_v2.txt": narrative_obj["text"].encode("utf-8"),
    }
    if world_diff is not None and world_diff_narrative is not None:
        planned_files["world_diff.json"] = dumps_canonical(world_diff)
        planned_files["world_diff_narrative.json"] = dumps_canonical(
            world_diff_narrative
        )
    if constraint_diff is not None and constraint_diff_narrative is not None:
        planned_files["constraint_diff.json"] = dumps_canonical(constraint_diff)
        planned_files["constraint_diff_narrative_v2.json"] = dumps_canonical(
            constraint_diff_narrative
        )
    for relpath, data in sorted(planned_files.items()):
        _write_or_verify(run_dir / relpath, data)

    return {
        "patch": patch_obj,
        "patch_sha256": patch_sha256,
        "output": built["output_obj"],
        "sealed": sealed,
        "result": patch_result,
        "narrative": narrative_obj,
        "world_diff": world_diff,
        "constraint_diff": constraint_diff,
        "run_dir": str(run_dir.resolve().as_posix()),
        "ledger_dir": built["ledger_dir"],
    }
