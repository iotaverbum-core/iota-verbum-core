from __future__ import annotations

import json
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _read_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_sealed_output_from_ledger_dir(path: str) -> dict:
    run_dir = Path(path)
    output_bytes = (run_dir / "output.json").read_bytes()
    attestation_bytes = (run_dir / "attestation.json").read_bytes()
    return {
        "output": json.loads(output_bytes.decode("utf-8")),
        "__meta__": {
            "output_sha256": sha256_bytes(output_bytes),
            "attestation_sha256": sha256_bytes(attestation_bytes),
        },
    }


def _load_output_input(path: str) -> dict:
    input_path = Path(path)
    if input_path.is_dir():
        return load_sealed_output_from_ledger_dir(path)
    output_bytes = input_path.read_bytes()
    return {
        "output": json.loads(output_bytes.decode("utf-8")),
        "__meta__": {
            "output_sha256": sha256_bytes(output_bytes),
            "attestation_sha256": "",
        },
    }


def _unwrap_output_and_meta(raw_output: dict) -> tuple[dict, dict]:
    if "output" in raw_output and isinstance(raw_output["output"], dict):
        return raw_output["output"], raw_output.get("__meta__", {})
    return raw_output, raw_output.get("__meta__", {})


def _extract_world_model(raw_output: dict) -> tuple[dict, dict]:
    output_obj, meta = _unwrap_output_and_meta(raw_output)
    if "world_model" in output_obj:
        return output_obj["world_model"], meta
    if "output" in output_obj and "world_model" in output_obj["output"]:
        return output_obj["output"]["world_model"], meta
    raise ValueError("sealed output missing world_model")


def _extract_verification_result(raw_output: dict) -> dict:
    output_obj, _meta = _unwrap_output_and_meta(raw_output)
    if "verification_result" in output_obj:
        return output_obj["verification_result"]
    if "output" in output_obj and "verification_result" in output_obj["output"]:
        return output_obj["output"]["verification_result"]
    raise ValueError("sealed output missing verification_result")


def _hash_meta(world_model: dict, meta: dict, output_obj: dict) -> dict:
    output_sha256 = meta.get("output_sha256")
    if output_sha256 is None:
        output_sha256 = sha256_bytes(dumps_canonical(output_obj))
    return {
        "world_sha256": world_model.get("world_sha256", ""),
        "output_sha256": output_sha256,
        "attestation_sha256": meta.get("attestation_sha256", ""),
    }


def _map_by_id(items: list[dict], id_field: str) -> dict[str, dict]:
    return {item[id_field]: item for item in items}


def _entity_diff(old_world: dict, new_world: dict) -> dict:
    old_ids = sorted(entity["entity_id"] for entity in old_world["entities"])
    new_ids = sorted(entity["entity_id"] for entity in new_world["entities"])
    old_set = set(old_ids)
    new_set = set(new_ids)
    return {
        "added": sorted(new_set - old_set),
        "removed": sorted(old_set - new_set),
        "unchanged": sorted(old_set & new_set),
    }


def _event_diff(old_world: dict, new_world: dict) -> dict:
    old_map = _map_by_id(old_world["events"], "event_id")
    new_map = _map_by_id(new_world["events"], "event_id")
    old_ids = set(old_map)
    new_ids = set(new_map)
    common_ids = sorted(old_ids & new_ids)
    changed = []
    unchanged = []
    for event_id in common_ids:
        if dumps_canonical(old_map[event_id]) == dumps_canonical(new_map[event_id]):
            unchanged.append(event_id)
            continue
        changes = []
        for field in ["type", "time", "actors", "objects", "action", "state"]:
            if dumps_canonical(old_map[event_id][field]) == dumps_canonical(
                new_map[event_id][field]
            ):
                continue
            changes.append(
                {
                    "field": field,
                    "old": old_map[event_id][field],
                    "new": new_map[event_id][field],
                }
            )
        changed.append(
            {
                "event_id": event_id,
                "changes": sorted(changes, key=lambda item: item["field"]),
            }
        )
    return {
        "added": sorted(new_ids - old_ids),
        "removed": sorted(old_ids - new_ids),
        "changed": sorted(changed, key=lambda item: item["event_id"]),
        "unchanged": unchanged,
    }


def _diff_object_lists(
    old_items: list[dict],
    new_items: list[dict],
    *,
    sort_fn,
) -> tuple[list[dict], list[dict]]:
    old_map = {_sort_key(item): item for item in old_items}
    new_map = {_sort_key(item): item for item in new_items}
    added_keys = sorted(set(new_map) - set(old_map))
    removed_keys = sorted(set(old_map) - set(new_map))
    return (
        sorted([new_map[key] for key in added_keys], key=sort_fn),
        sorted([old_map[key] for key in removed_keys], key=sort_fn),
    )


def _unknown_sort_key(item: dict) -> tuple[str, str]:
    return (item["kind"], _sort_key(item["ref"]))


def _conflict_sort_key(item: dict) -> tuple[str, str]:
    return (item["kind"], _sort_key(item["ref"]))


def _reason_sort_key(item: dict) -> tuple[str, str]:
    return (item["code"], _sort_key(item["ref"]))


def compute_world_diff(*, old_output: dict, new_output: dict) -> dict:
    old_output_obj, old_meta = _unwrap_output_and_meta(old_output)
    new_output_obj, new_meta = _unwrap_output_and_meta(new_output)
    old_world, _ = _extract_world_model(old_output)
    new_world, _ = _extract_world_model(new_output)
    old_verification = _extract_verification_result(old_output)
    new_verification = _extract_verification_result(new_output)

    entities = _entity_diff(old_world, new_world)
    events = _event_diff(old_world, new_world)
    unknowns_added, unknowns_removed = _diff_object_lists(
        old_world["unknowns"],
        new_world["unknowns"],
        sort_fn=_unknown_sort_key,
    )
    conflicts_added, conflicts_removed = _diff_object_lists(
        old_world["conflicts"],
        new_world["conflicts"],
        sort_fn=_conflict_sort_key,
    )
    reasons_added, reasons_removed = _diff_object_lists(
        old_verification["reasons"],
        new_verification["reasons"],
        sort_fn=_reason_sort_key,
    )
    required_info_added, required_info_removed = _diff_object_lists(
        old_verification["required_info"],
        new_verification["required_info"],
        sort_fn=_unknown_sort_key,
    )

    diff = {
        "world_diff_version": "1.0",
        "old": _hash_meta(old_world, old_meta, old_output_obj),
        "new": _hash_meta(new_world, new_meta, new_output_obj),
        "entities": entities,
        "events": events,
        "unknowns": {
            "added": unknowns_added,
            "removed": unknowns_removed,
        },
        "conflicts": {
            "added": conflicts_added,
            "removed": conflicts_removed,
        },
        "verification": {
            "old_status": old_verification["status"],
            "new_status": new_verification["status"],
            "reasons_added": reasons_added,
            "reasons_removed": reasons_removed,
            "required_info_added": required_info_added,
            "required_info_removed": required_info_removed,
        },
    }
    validate(diff, "schemas/world_diff.schema.json")
    return diff


def load_output_input(path: str) -> dict:
    return _load_output_input(path)
