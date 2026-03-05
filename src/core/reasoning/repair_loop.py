from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.finalize import finalize
from core.determinism.hashing import sha256_bytes
from core.determinism.ledger import write_run
from core.determinism.replay import verify_run
from core.determinism.schema_validate import validate
from core.reasoning.causal import compute_causal_graph
from core.reasoning.causal_narrative_v2 import render_causal_narrative_v2
from core.reasoning.constraint_diff import compute_constraint_diff
from core.reasoning.constraint_narrative_v2 import render_constraint_narrative_v2
from core.reasoning.constraints import compute_constraints
from core.reasoning.counterfactual import load_base_output
from core.reasoning.critical_path import compute_critical_path
from core.reasoning.critical_path_narrative_v2 import render_critical_path_narrative_v2
from core.reasoning.repair_hints import compute_repair_hints
from core.reasoning.repair_hints_narrative_v2 import (
    render_repair_hints_narrative_v2,
)
from core.reasoning.repair_narrative_v2 import render_repair_narrative_v2
from core.reasoning.repair_plan import compute_repair_plan, repair_out_dir_name
from core.reasoning.verifier import verify_claim
from core.reasoning.world_diff import compute_world_diff
from core.reasoning.world_narrative_v2 import render_world_narrative_v2
from core.reasoning.world_patch import (
    _manifest_sha256,
    _repo_relative,
    run_world_patch,
)
from proposal.world_enrich import apply_world_enrichment
from proposal.world_propose import propose_world_model_from_artifacts


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def _write_or_verify(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"existing repair file mismatch: {path}")
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


def _extract_source_ref(source_kind: str, source_path: Path) -> dict:
    if source_kind == "ledger_dir":
        return {"ledger_dir": source_path.as_posix()}
    return {"output_json": source_path.as_posix()}


def _normalize_enrichment_template(enrichment_template: dict) -> dict:
    if enrichment_template.get("version", "") != "1.0":
        raise ValueError("world enrichment template version must be 1.0")
    missing_items = enrichment_template.get("missing", [])
    if not isinstance(missing_items, list):
        raise ValueError("world enrichment template missing must be an array")

    events_by_id: dict[str, dict] = {}
    unfilled: list[dict] = []
    for item in sorted(
        missing_items,
        key=lambda raw: (
            str(raw.get("kind", "")),
            str(raw.get("event_id", "")),
        ),
    ):
        kind = item.get("kind", "")
        event_id = item.get("event_id", "")
        value = item.get("value", None)
        if kind not in {"missing_time", "missing_actor", "missing_object"}:
            continue
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("world enrichment template event_id is required")
        if value is None:
            unfilled.append({"kind": kind, "event_id": event_id})
            continue

        patch = events_by_id.setdefault(event_id, {"event_id": event_id})
        if kind == "missing_time":
            if isinstance(value, str):
                patch["time"] = {"kind": "date", "value": value}
            elif isinstance(value, dict):
                patch["time"] = value
            else:
                raise ValueError("missing_time value must be string or object")
            continue

        if isinstance(value, str):
            value_list = [value]
        elif isinstance(value, list):
            value_list = [item for item in value if isinstance(item, str) and item]
        else:
            raise ValueError(f"{kind} value must be string or list[str]")
        if not value_list:
            raise ValueError(f"{kind} value list cannot be empty")
        field = "actors" if kind == "missing_actor" else "objects"
        patch[field] = sorted(set(value_list))

    world_enrichment = {
        "version": "1.0",
        "events": sorted(events_by_id.values(), key=lambda item: item["event_id"]),
    }
    return {
        "world_enrichment": world_enrichment,
        "unfilled": sorted(unfilled, key=lambda item: (item["kind"], item["event_id"])),
    }


def _synthetic_pack_from_bundle(bundle_obj: dict) -> dict:
    docs_by_source: dict[str, dict] = {}
    chunks = []
    for index, artifact in enumerate(bundle_obj["artifacts"]):
        source_id = artifact["source_id"]
        doc = docs_by_source.setdefault(
            source_id,
            {
                "doc_id": source_id,
                "relpath": source_id,
                "sha256": "0" * 64,
                "bytes": 0,
            },
        )
        doc["bytes"] += len(artifact["text"].encode("utf-8"))
        chunks.append(
            {
                "doc_id": source_id,
                "chunk_id": artifact["chunk_id"],
                "index": index,
                "offset_start": artifact["offset_start"],
                "offset_end": artifact["offset_end"],
                "text": artifact["text"],
                "text_sha256": artifact["text_sha256"],
            }
        )
    pack = {
        "pack_version": "1.0",
        "root_hint": "bundle_artifacts",
        "documents": sorted(
            docs_by_source.values(),
            key=lambda item: (item["relpath"], item["doc_id"]),
        ),
        "chunks": sorted(
            chunks,
            key=lambda item: (
                item["doc_id"],
                item["index"],
                item["chunk_id"],
            ),
        ),
        "pack_sha256": "",
    }
    pack_for_hash = deepcopy(pack)
    pack_for_hash["pack_sha256"] = ""
    pack["pack_sha256"] = sha256_bytes(dumps_canonical(pack_for_hash))
    return pack


def _build_tuned_output(
    *,
    base_loaded: dict,
    query: str,
    max_chunks: int,
    max_events: int,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    out_ledger_root: str,
    mode: str,
    max_lines: int,
) -> dict:
    pack = _synthetic_pack_from_bundle(base_loaded["bundle_obj"])
    world_model = propose_world_model_from_artifacts(
        pack,
        base_loaded["bundle_obj"]["artifacts"],
        query=query,
        max_chunks=max_chunks,
        max_events=max_events,
    )
    return _build_world_output(
        base_loaded=base_loaded,
        world_model=world_model,
        created_utc=created_utc,
        core_version=core_version,
        ruleset_id=ruleset_id,
        ledger_root=out_ledger_root,
        mode=mode,
        max_lines=max_lines,
    )


def _build_world_output(
    *,
    base_loaded: dict,
    world_model: dict,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    ledger_root: str,
    mode: str,
    max_lines: int,
) -> dict:
    causal_graph = compute_causal_graph(world_model)
    critical_path = compute_critical_path(causal_graph)
    constraint_report = compute_constraints(world_model, causal_graph)
    repair_hints = compute_repair_hints(constraint_report, causal_graph, world_model)
    target_claim_id = base_loaded["output_obj"]["verification_result"][
        "target_claim_id"
    ]
    output_obj = {
        "world_model": world_model,
        "causal_graph": causal_graph,
        "causal_findings": causal_graph["findings"],
        "critical_path": critical_path,
        "constraint_report": constraint_report,
        "repair_hints": repair_hints,
    }
    verification_result = verify_claim(
        ruleset_id=ruleset_id,
        target_claim_id=target_claim_id,
        evidence_bundle_obj=base_loaded["bundle_obj"],
        sealed_output_obj=output_obj,
    )
    output_obj["world_narrative_v2"] = render_world_narrative_v2(
        world_model=world_model,
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
        base_loaded["bundle_obj"],
        output_obj,
        manifest_sha256=_manifest_sha256(),
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


def _apply_add_world_enrichment(
    *,
    base_loaded: dict,
    action: dict,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    out_ledger_root: str,
    mode: str,
    max_lines: int,
) -> tuple[int, dict | None, str]:
    template_path = Path(action["inputs"]["enrichment_path"])
    if not template_path.exists():
        print("fill these values")
        print(f"- missing enrichment template: {template_path.as_posix()}")
        return 2, None, ""

    template_obj = json.loads(template_path.read_text(encoding="utf-8"))
    normalized = _normalize_enrichment_template(template_obj)
    unfilled = normalized["unfilled"]
    if unfilled:
        print("fill these values")
        for item in unfilled:
            print(f"- {item['kind']} {item['event_id']}")
        return 2, None, ""

    world_enrichment = normalized["world_enrichment"]
    enriched_world = apply_world_enrichment(
        base_loaded["output_obj"]["world_model"],
        world_enrichment,
    )
    built = _build_world_output(
        base_loaded=base_loaded,
        world_model=enriched_world,
        created_utc=created_utc,
        core_version=core_version,
        ruleset_id=ruleset_id,
        ledger_root=out_ledger_root,
        mode=mode,
        max_lines=max_lines,
    )
    return 0, built, ""


def _apply_world_patch_action(
    *,
    base: str,
    run_dir: Path,
    action: dict,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
) -> tuple[int, dict | None, str]:
    patch_path = str(action["inputs"].get("patch_path", "")).strip()
    if not patch_path:
        print("fill these values")
        print("- patch path is required")
        return 2, None, ""
    if not Path(patch_path).exists():
        print("fill these values")
        print(f"- missing patch file: {patch_path}")
        return 2, None, ""

    patch_result = run_world_patch(
        base=base,
        patch=patch_path,
        out_dir=str((run_dir / "world_patch").as_posix()),
        created_utc=created_utc,
        core_version=core_version,
        ruleset_id=ruleset_id,
        with_diff=False,
        with_constraint_diff=False,
        mode="brief",
        max_lines=120,
    )
    return 0, patch_result, patch_path


def _apply_tune_focus_action(
    *,
    base_loaded: dict,
    run_dir: Path,
    action: dict,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
) -> tuple[int, dict | None]:
    inputs = action["inputs"]
    query = str(inputs["recommended_query"])
    max_chunks = int(inputs["recommended_max_chunks"])
    max_events = int(inputs["recommended_max_events"])
    built = _build_tuned_output(
        base_loaded=base_loaded,
        query=query,
        max_chunks=max_chunks,
        max_events=max_events,
        created_utc=created_utc,
        core_version=core_version,
        ruleset_id=ruleset_id,
        out_ledger_root=str((run_dir / "ledger").as_posix()),
        mode="brief",
        max_lines=120,
    )
    return 0, built


def run_repair_loop(
    *,
    base: str,
    out_dir: str,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    approve: bool,
    choose: int | None,
    strict_manifest: bool,
    mode: str = "brief",
    max_lines: int = 120,
) -> int:
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

    plan = compute_repair_plan(
        {
            "output": base_output_obj,
            "__meta__": {
                "output_sha256": base_loaded["output_sha256"],
                "attestation_sha256": base_loaded["attestation_sha256"],
            },
            "__bundle_params": base_loaded["bundle_obj"]["inputs"]["params"],
            "__source_ref": _extract_source_ref(source_kind, base_path),
        },
        ruleset_id,
    )

    run_dir = _resolve_run_dir(
        Path(out_dir) / repair_out_dir_name(plan["plan_id"]),
        {"repair_plan.json": dumps_canonical(plan)},
    )
    _write_or_verify(run_dir / "repair_plan.json", dumps_canonical(plan))

    if not approve:
        narrative_obj = render_repair_narrative_v2(
            plan,
            None,
            mode=mode,
            max_lines=max_lines,
        )
        _write_or_verify(
            run_dir / "repair_narrative_v2.json",
            dumps_canonical(narrative_obj),
        )
        _write_or_verify(
            run_dir / "repair_narrative_v2.txt",
            narrative_obj["text"].encode("utf-8"),
        )
        print(narrative_obj["text"], end="")
        return 2

    if not plan["actions"]:
        print("No repair actions available for VERIFIED_OK plan.")
        return 2

    selected_index = choose if choose is not None else 0
    if selected_index < 0 or selected_index >= len(plan["actions"]):
        raise ValueError(f"choose index out of range: {selected_index}")
    selected_action = plan["actions"][selected_index]

    execution_result: dict | None = None
    applied_changes = {"kind": selected_action["kind"]}
    if selected_action["kind"] == "ADD_WORLD_ENRICHMENT":
        exit_code, execution_result, _ = _apply_add_world_enrichment(
            base_loaded=base_loaded,
            action=selected_action,
            created_utc=created_utc,
            core_version=core_version,
            ruleset_id=ruleset_id,
            out_ledger_root=str((run_dir / "ledger").as_posix()),
            mode=mode,
            max_lines=max_lines,
        )
        if exit_code != 0:
            return exit_code
        applied_changes["enrichment_path"] = selected_action["inputs"][
            "enrichment_path"
        ]
    elif selected_action["kind"] == "APPLY_WORLD_PATCH":
        exit_code, execution_result, patch_path = _apply_world_patch_action(
            base=str(base_path.as_posix()),
            run_dir=run_dir,
            action=selected_action,
            created_utc=created_utc,
            core_version=core_version,
            ruleset_id=ruleset_id,
        )
        if exit_code != 0:
            return exit_code
        applied_changes["patch_path"] = patch_path
    elif selected_action["kind"] == "TUNE_FOCUS":
        exit_code, execution_result = _apply_tune_focus_action(
            base_loaded=base_loaded,
            run_dir=run_dir,
            action=selected_action,
            created_utc=created_utc,
            core_version=core_version,
            ruleset_id=ruleset_id,
        )
        if exit_code != 0:
            return exit_code
        applied_changes["query"] = selected_action["inputs"]["recommended_query"]
        applied_changes["max_chunks"] = selected_action["inputs"][
            "recommended_max_chunks"
        ]
        applied_changes["max_events"] = selected_action["inputs"][
            "recommended_max_events"
        ]
    else:
        raise ValueError(f"unsupported repair action kind: {selected_action['kind']}")

    assert execution_result is not None
    new_output_obj = execution_result["output_obj"]
    new_sealed = execution_result["sealed"]
    new_ledger_dir = execution_result["ledger_dir"]

    world_diff = compute_world_diff(
        old_output=_sealed_output_wrapper(
            base_output_obj,
            output_sha256=base_loaded["output_sha256"],
            attestation_sha256=base_loaded["attestation_sha256"],
        ),
        new_output=_sealed_output_wrapper(
            new_output_obj,
            output_sha256=new_sealed["output_sha256"],
            attestation_sha256=new_sealed["attestation_sha256"],
        ),
    )
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
            new_output_obj,
            output_sha256=new_sealed["output_sha256"],
            attestation_sha256=new_sealed["attestation_sha256"],
        ),
    )

    try:
        replay = verify_run(new_ledger_dir, strict_manifest=strict_manifest)
    except Exception:
        replay = {"ok": False, "strict_manifest": strict_manifest, "warnings": []}
        return_code = 1
    else:
        replay = {
            **replay,
            "strict_manifest": strict_manifest,
        }
        return_code = 0

    run_record = {
        "version": "1.0",
        "plan_id": plan["plan_id"],
        "selected_action_id": selected_action["action_id"],
        "base": {
            **plan["base"],
            "source_ref": (
                {"kind": source_kind, "path": base_path.as_posix()}
            ),
        },
        "new": {
            "world_sha256": new_output_obj["world_model"]["world_sha256"],
            "output_sha256": new_sealed["output_sha256"],
            "attestation_sha256": new_sealed["attestation_sha256"],
            "ledger_dir": _repo_relative(Path(new_ledger_dir)),
        },
        "verification": {
            "old": base_output_obj["verification_result"]["status"],
            "new": new_output_obj["verification_result"]["status"],
        },
        "diffs": {
            "world_diff_present": bool(world_diff),
            "constraint_diff_present": bool(constraint_diff),
        },
        "replay": {
            "strict_manifest": strict_manifest,
            "ok": bool(replay["ok"]),
        },
        "receipts": {
            "action_receipts": deepcopy(selected_action["receipts"]),
        },
        "applied_changes": applied_changes,
    }
    validate(run_record, "schemas/repair_run_record.schema.json")

    narrative_obj = render_repair_narrative_v2(
        plan,
        run_record,
        mode=mode,
        max_lines=max_lines,
    )

    planned_files = {
        "repair_plan.json": dumps_canonical(plan),
        "repair_run_record.json": dumps_canonical(run_record),
        "repair_narrative_v2.json": dumps_canonical(narrative_obj),
        "repair_narrative_v2.txt": narrative_obj["text"].encode("utf-8"),
        "output.json": new_sealed["output_bytes"],
        "attestation.json": new_sealed["attestation_bytes"],
        "world_diff.json": dumps_canonical(world_diff),
        "constraint_diff.json": dumps_canonical(constraint_diff),
    }
    for relpath, data in sorted(planned_files.items()):
        _write_or_verify(run_dir / relpath, data)

    print(narrative_obj["text"], end="")
    return return_code
