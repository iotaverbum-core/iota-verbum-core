from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.finalize import finalize
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate
from core.reasoning.causal import compute_causal_graph
from core.reasoning.causal_narrative_v2 import render_causal_narrative_v2
from core.reasoning.counterfactual_narrative_v2 import (
    render_counterfactual_narrative_v2,
)
from core.reasoning.verifier import verify_claim
from core.reasoning.world_diff import compute_world_diff
from core.reasoning.world_diff_narrative import render_world_diff_narrative


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


_TASK_ID_RE = re.compile(r"^cf:[0-9a-f]{64}$")


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
            raise ValueError(f"existing counterfactual file mismatch: {path}")
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


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_sibling(base_path: Path, names: list[str]) -> Path:
    for name in names:
        candidate = base_path.parent / name
        if candidate.exists():
            return candidate
    raise ValueError(
        f"required sibling artifact not found next to {base_path}: {', '.join(names)}"
    )


def _task_for_hash(task: dict) -> dict:
    hashed = deepcopy(task)
    hashed.pop("task_id", None)
    return hashed


def compute_counterfactual_task_id(task_without_task_id: dict) -> str:
    return "cf:" + sha256_bytes(dumps_canonical(_task_for_hash(task_without_task_id)))


def compute_task_id(task: dict) -> str:
    return compute_counterfactual_task_id(task)


def _normalize_legacy_task(task: dict) -> dict:
    normalized = deepcopy(task)
    if (
        "task_id" in normalized
        and _TASK_ID_RE.match(str(normalized["task_id"])) is None
    ):
        normalized["task_id"] = ""
    if "base" in normalized and "source" not in normalized["base"]:
        if "ledger_dir" in normalized["base"]:
            normalized["base"] = {
                **{
                    key: value
                    for key, value in normalized["base"].items()
                    if key != "ledger_dir"
                },
                "source": {
                    "kind": "ledger_dir",
                    "path": normalized["base"]["ledger_dir"],
                },
            }
        elif "output_json" in normalized["base"]:
            normalized["base"] = {
                **{
                    key: value
                    for key, value in normalized["base"].items()
                    if key != "output_json"
                },
                "source": {
                    "kind": "output_json",
                    "path": normalized["base"]["output_json"],
                },
            }
    if "actions" in normalized and "operation" not in normalized:
        actions = normalized.pop("actions")
        if len(actions) != 1:
            raise ValueError("counterfactual tasks must have exactly one action")
        action = actions[0]
        if action["kind"] == "REMOVE_EVENT":
            normalized["operation"] = {
                "type": "REMOVE_EVENT",
                "target_id": action["event_id"],
            }
        elif action["kind"] == "REMOVE_ENTITY":
            normalized["operation"] = {
                "type": "REMOVE_ENTITY",
                "target_id": action["entity_id"],
            }
        else:
            raise ValueError(
                f"unsupported counterfactual action kind: {action['kind']}"
            )
    normalized.setdefault("created_utc", "1970-01-01T00:00:00Z")
    normalized.setdefault("options", {"mode": "brief", "max_lines": 80})
    return normalized


def _validate_and_finalize_task(task: dict) -> dict:
    normalized = _normalize_legacy_task(task)
    validate(normalized, "schemas/counterfactual_task.schema.json")
    return normalized


def _counterfactual_task_error(expected_task_id: str) -> ValueError:
    return ValueError(
        "counterfactual task_id does not match canonical task hash; "
        f"expected task_id={expected_task_id}. "
        "Run cli_counterfactual with --fix-task true to rewrite the file."
    )


def canonicalize_counterfactual_task(task: dict) -> bytes:
    final_task = _validate_and_finalize_task(task)
    final_task["task_id"] = compute_counterfactual_task_id(final_task)
    validate(final_task, "schemas/counterfactual_task.schema.json")
    return dumps_canonical(final_task)


def canonicalize_counterfactual_task_file(path: str | Path) -> str:
    raw_task = _load_json(Path(path))
    canonical_bytes = canonicalize_counterfactual_task(raw_task)
    _write_atomic(Path(path), canonical_bytes)
    canonical_task = json.loads(canonical_bytes.decode("utf-8"))
    return canonical_task["task_id"]


def load_counterfactual_task(path: str) -> tuple[dict, bytes]:
    raw_task = _load_json(Path(path))
    normalized_task = _validate_and_finalize_task(raw_task)
    expected_task_id = compute_counterfactual_task_id(normalized_task)
    if normalized_task.get("task_id", "") != expected_task_id:
        raise _counterfactual_task_error(expected_task_id)
    validate(normalized_task, "schemas/counterfactual_task.schema.json")
    return normalized_task, dumps_canonical(normalized_task)


def _entity_sort_key(entity: dict) -> tuple[str, str, str]:
    return (entity["type"], entity["name"], entity["entity_id"])


def _event_sort_key(event: dict) -> tuple[int, str, str]:
    time_ref = event["time"]
    if time_ref["kind"] == "unknown":
        return (1, "", event["event_id"])
    return (0, time_ref["value"], event["event_id"])


def _sort_json_ref(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _compute_world_sha256(world_obj: dict) -> str:
    world_for_hash = deepcopy(world_obj)
    world_for_hash["world_sha256"] = ""
    return sha256_bytes(dumps_canonical(world_for_hash))


def _build_relations(events: list[dict]) -> list[dict]:
    known_events = [event for event in events if event["time"]["kind"] != "unknown"]
    known_events.sort(key=lambda event: (event["time"]["value"], event["event_id"]))
    relations = []
    for previous, current in zip(known_events, known_events[1:]):
        relation_type = (
            "same_time"
            if previous["time"]["value"] == current["time"]["value"]
            else "before"
        )
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


def _normalize_world_model(world_model: dict) -> dict:
    entities = sorted(
        [deepcopy(entity) for entity in world_model["entities"]],
        key=_entity_sort_key,
    )
    events = sorted(
        [deepcopy(event) for event in world_model["events"]],
        key=_event_sort_key,
    )
    normalized = {
        "world_version": "1.0",
        "world_sha256": "",
        "entities": entities,
        "events": events,
        "relations": _build_relations(events),
        "unknowns": _build_unknowns(events),
        "conflicts": _build_conflicts(events, entities),
    }
    normalized["world_sha256"] = _compute_world_sha256(normalized)
    validate(normalized, "schemas/world_model.schema.json")
    return normalized


def _load_attestation(source_kind: str, source_path: Path) -> tuple[dict, bytes, str]:
    if source_kind == "ledger_dir":
        attestation_path = source_path / "attestation.json"
    else:
        attestation_path = _load_sibling(source_path, ["attestation.json"])
    attestation_bytes = attestation_path.read_bytes()
    attestation_obj = json.loads(attestation_bytes.decode("utf-8"))
    validate(attestation_obj, "schemas/attestation_record.schema.json")
    return attestation_obj, attestation_bytes, sha256_bytes(attestation_bytes)


def _load_bundle(source_kind: str, source_path: Path) -> tuple[dict, bytes, str]:
    if source_kind == "ledger_dir":
        bundle_path = source_path / "bundle.json"
    else:
        bundle_path = _load_sibling(
            source_path,
            ["evidence_bundle.json", "bundle.json"],
        )
    bundle_bytes = bundle_path.read_bytes()
    bundle_obj = json.loads(bundle_bytes.decode("utf-8"))
    validate(bundle_obj, "schemas/evidence_bundle.schema.json")
    return bundle_obj, bundle_bytes, sha256_bytes(bundle_bytes)


def load_base_output(source: dict) -> dict:
    source_kind = source["kind"]
    source_path = Path(source["path"]).resolve()
    output_path = (
        source_path / "output.json"
        if source_kind == "ledger_dir"
        else source_path
    )
    output_bytes = output_path.read_bytes()
    output_obj = json.loads(output_bytes.decode("utf-8"))
    bundle_obj, bundle_bytes, bundle_sha256 = _load_bundle(source_kind, source_path)
    attestation_obj, attestation_bytes, attestation_sha256 = _load_attestation(
        source_kind,
        source_path,
    )
    return {
        "source_kind": source_kind,
        "source_path": str(source_path.as_posix()),
        "output_obj": output_obj,
        "output_bytes": output_bytes,
        "output_sha256": sha256_bytes(output_bytes),
        "bundle_obj": bundle_obj,
        "bundle_bytes": bundle_bytes,
        "bundle_sha256": bundle_sha256,
        "attestation_obj": attestation_obj,
        "attestation_bytes": attestation_bytes,
        "attestation_sha256": attestation_sha256,
    }


def _validate_base_task_hashes(task: dict, base_loaded: dict) -> None:
    base = task["base"]
    if (
        "bundle_sha256" in base
        and base["bundle_sha256"] != base_loaded["bundle_sha256"]
    ):
        raise ValueError("counterfactual task bundle_sha256 does not match base bundle")
    world_sha256 = base_loaded["output_obj"]["world_model"]["world_sha256"]
    if "world_sha256" in base and base["world_sha256"] != world_sha256:
        raise ValueError("counterfactual task world_sha256 does not match base output")
    if (
        "attestation_sha256" in base
        and base["attestation_sha256"] != base_loaded["attestation_sha256"]
    ):
        raise ValueError(
            "counterfactual task attestation_sha256 does not match base attestation"
        )


def apply_counterfactual(world_model: dict, operation: dict) -> dict:
    validate(world_model, "schemas/world_model.schema.json")
    operation_type = operation["type"]
    target_id = operation["target_id"]
    updated = deepcopy(world_model)

    if operation_type == "REMOVE_EVENT":
        if target_id not in {event["event_id"] for event in updated["events"]}:
            raise ValueError(f"counterfactual event not found: {target_id}")
        updated["events"] = [
            event for event in updated["events"] if event["event_id"] != target_id
        ]
    elif operation_type == "REMOVE_ENTITY":
        if target_id not in {entity["entity_id"] for entity in updated["entities"]}:
            raise ValueError(f"counterfactual entity not found: {target_id}")
        updated["entities"] = [
            entity for entity in updated["entities"] if entity["entity_id"] != target_id
        ]
        updated["events"] = [
            {
                **deepcopy(event),
                "actors": sorted(
                    actor for actor in event["actors"] if actor != target_id
                ),
                "objects": sorted(
                    obj for obj in event["objects"] if obj != target_id
                ),
            }
            for event in updated["events"]
        ]
    else:
        raise ValueError(f"unsupported counterfactual operation: {operation_type}")

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


def _counterfactual_dir_name(task_id: str) -> str:
    return task_id.replace(":", "_")


def _build_counterfactual_output(
    *,
    world_model: dict,
    bundle_obj: dict,
    target_claim_id: str,
    ruleset_id: str,
    mode: str,
    max_lines: int,
) -> dict:
    causal_graph = compute_causal_graph(world_model)
    output_obj = {
        "world_model": world_model,
        "causal_graph": causal_graph,
        "causal_findings": causal_graph["findings"],
    }
    verification_result = verify_claim(
        ruleset_id=ruleset_id,
        target_claim_id=target_claim_id,
        evidence_bundle_obj=bundle_obj,
        sealed_output_obj=output_obj,
    )
    output_obj["causal_narrative_v2"] = render_causal_narrative_v2(
        causal_graph,
        verification_result=verification_result,
        max_lines=max_lines,
        verbosity=mode,
    )
    output_obj["verification_result"] = verification_result
    return output_obj


def run_counterfactual_task(
    task: dict,
    *,
    out_dir: str,
    mode_override: str | None = None,
) -> dict:
    validate(task, "schemas/counterfactual_task.schema.json")
    expected_task_id = compute_counterfactual_task_id(task)
    if task.get("task_id") != expected_task_id:
        raise _counterfactual_task_error(expected_task_id)
    effective_mode = mode_override or task["options"]["mode"]

    base_loaded = load_base_output(task["base"]["source"])
    _validate_base_task_hashes(task, base_loaded)
    base_output = base_loaded["output_obj"]
    if "world_model" not in base_output or "verification_result" not in base_output:
        raise ValueError("base output missing world_model or verification_result")
    if "causal_graph" not in base_output:
        raise ValueError("base output missing causal_graph")

    new_world_model = apply_counterfactual(
        base_output["world_model"],
        task["operation"],
    )
    counterfactual_output = _build_counterfactual_output(
        world_model=new_world_model,
        bundle_obj=base_loaded["bundle_obj"],
        target_claim_id=base_output["verification_result"]["target_claim_id"],
        ruleset_id=base_output["verification_result"]["ruleset_id"],
        mode=effective_mode,
        max_lines=task["options"]["max_lines"],
    )
    sealed = finalize(
        base_loaded["bundle_obj"],
        counterfactual_output,
        manifest_sha256=_manifest_sha256(),
        core_version=base_loaded["bundle_obj"]["toolchain"]["core_version"],
        ruleset_id=base_loaded["bundle_obj"]["policy"]["ruleset_id"],
        created_utc=task["created_utc"],
    )
    diff = compute_world_diff(
        old_output=_sealed_output_wrapper(
            base_output,
            output_sha256=base_loaded["output_sha256"],
            attestation_sha256=base_loaded["attestation_sha256"],
        ),
        new_output=_sealed_output_wrapper(
            counterfactual_output,
            output_sha256=sealed["output_sha256"],
            attestation_sha256=sealed["attestation_sha256"],
        ),
    )
    world_diff_narrative = render_world_diff_narrative(
        diff,
        mode=effective_mode,
        max_lines=task["options"]["max_lines"],
    )
    changed_events = [
        {
            "event_id": item["event_id"],
            "fields_changed": [change["field"] for change in item["changes"]],
        }
        for item in diff["events"]["changed"]
    ]
    changed_events.sort(key=lambda item: item["event_id"])
    result_obj = {
        "version": "1.0",
        "task_id": task["task_id"],
        "base_hashes": {
            "world_sha256": base_output["world_model"]["world_sha256"],
            "output_sha256": base_loaded["output_sha256"],
            "attestation_sha256": base_loaded["attestation_sha256"],
        },
        "counterfactual_hashes": {
            "world_sha256": counterfactual_output["world_model"]["world_sha256"],
            "output_sha256": sealed["output_sha256"],
            "attestation_sha256": sealed["attestation_sha256"],
        },
        "operation": deepcopy(task["operation"]),
        "effects": {
            "removed": {
                "events": diff["events"]["removed"],
                "entities": diff["entities"]["removed"],
            },
            "changed_events": changed_events,
            "changed_unknowns_count": {
                "old": len(base_output["world_model"]["unknowns"]),
                "new": len(counterfactual_output["world_model"]["unknowns"]),
            },
            "verification_change": {
                "old": base_output["verification_result"]["status"],
                "new": counterfactual_output["verification_result"]["status"],
            },
        },
        "diff": diff,
        "receipts": {
            "base_path": base_loaded["source_path"],
            "counterfactual_path": "",
        },
    }
    validate(diff, "schemas/world_diff.schema.json")
    planned_files = {
        "task.json": dumps_canonical(task),
        "output.json": sealed["output_bytes"],
        "attestation.json": sealed["attestation_bytes"],
        "world_diff.json": dumps_canonical(diff),
        "world_diff_narrative.json": dumps_canonical(world_diff_narrative),
    }
    run_root = Path(out_dir)
    base_run_dir = run_root / _counterfactual_dir_name(task["task_id"])
    narrative_obj = None
    result_bytes = b""
    run_dir = base_run_dir
    while True:
        run_dir = _resolve_run_dir(base_run_dir, planned_files)
        resolved_run_dir = str(run_dir.resolve().as_posix())
        if result_obj["receipts"]["counterfactual_path"] == resolved_run_dir:
            break
        result_obj["receipts"]["counterfactual_path"] = resolved_run_dir
        result_bytes = dumps_canonical(result_obj)
        narrative_task = deepcopy(task)
        narrative_task["options"]["mode"] = effective_mode
        narrative_obj = render_counterfactual_narrative_v2(
            task=narrative_task,
            result=result_obj,
            world_diff_narrative=world_diff_narrative,
            base_output=base_output,
            counterfactual_output=counterfactual_output,
        )
        validate(result_obj, "schemas/counterfactual_result.schema.json")
        validate(narrative_obj, "schemas/counterfactual_narrative_v2.schema.json")
        planned_files["counterfactual_result.json"] = result_bytes
        planned_files["counterfactual_narrative_v2.json"] = dumps_canonical(
            narrative_obj
        )
        planned_files["counterfactual_narrative_v2.txt"] = narrative_obj["text"].encode(
            "utf-8"
        )
    assert narrative_obj is not None
    for relpath, data in sorted(planned_files.items()):
        _write_or_verify(run_dir / relpath, data)
    return {
        "task": task,
        "base_output": base_output,
        "counterfactual_output": counterfactual_output,
        "output_bytes": sealed["output_bytes"],
        "output_sha256": sealed["output_sha256"],
        "attestation_bytes": sealed["attestation_bytes"],
        "attestation_sha256": sealed["attestation_sha256"],
        "result": result_obj,
        "result_bytes": result_bytes,
        "narrative": narrative_obj,
        "world_diff": diff,
        "world_diff_narrative": world_diff_narrative,
        "run_dir": str(run_dir.resolve().as_posix()),
    }
