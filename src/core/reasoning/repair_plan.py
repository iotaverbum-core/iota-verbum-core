from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _extract_output_obj(base_output: dict) -> dict:
    if "output" in base_output and isinstance(base_output["output"], dict):
        return base_output["output"]
    return base_output


def _base_hashes(base_output: dict, output_obj: dict) -> dict:
    meta = base_output.get("__meta__", {})
    output_sha256 = meta.get("output_sha256", "")
    if not output_sha256:
        output_sha256 = sha256_bytes(dumps_canonical(output_obj))

    attestation_sha256 = meta.get("attestation_sha256", "")
    source_ref = base_output.get("__source_ref", {})

    base = {
        "world_sha256": output_obj["world_model"]["world_sha256"],
        "output_sha256": output_sha256,
        "attestation_sha256": attestation_sha256,
    }
    ledger_dir = source_ref.get("ledger_dir", "")
    if ledger_dir:
        base["ledger_dir"] = ledger_dir
    return base


def _collect_event_ids_from_verification(verification_result: dict) -> list[str]:
    event_ids = set()
    for reason in verification_result.get("reasons", []):
        ref = reason.get("ref", {})
        if isinstance(ref.get("event_id"), str):
            event_ids.add(ref["event_id"])
        if isinstance(ref.get("event_ids"), list):
            for event_id in ref["event_ids"]:
                if isinstance(event_id, str):
                    event_ids.add(event_id)
        if isinstance(ref.get("events"), list):
            for event_id in ref["events"]:
                if isinstance(event_id, str):
                    event_ids.add(event_id)
    return sorted(event_ids)


def _collect_entity_ids_from_verification(verification_result: dict) -> list[str]:
    entity_ids = set()
    for reason in verification_result.get("reasons", []):
        ref = reason.get("ref", {})
        if isinstance(ref.get("entity_id"), str):
            entity_ids.add(ref["entity_id"])
        if isinstance(ref.get("entities"), list):
            for entity_id in ref["entities"]:
                if isinstance(entity_id, str):
                    entity_ids.add(entity_id)
    return sorted(entity_ids)


def _collect_evidence_refs(verification_result: dict) -> list[dict]:
    refs = verification_result.get("receipts", {}).get("evidence_refs", [])
    unique: dict[str, dict] = {}
    for ref in refs:
        unique[_sort_key(ref)] = ref
    return [unique[key] for key in sorted(unique)]


def _action_id(action: dict) -> str:
    hashed = deepcopy(action)
    hashed["action_id"] = ""
    return "act:" + sha256_bytes(dumps_canonical(hashed))


def _plan_id(plan: dict) -> str:
    hashed = deepcopy(plan)
    hashed["plan_id"] = ""
    for action in hashed["actions"]:
        action["action_id"] = ""
    return "plan:" + sha256_bytes(dumps_canonical(hashed))


def _default_enrichment_path(output_obj: dict) -> str:
    repair_hints = output_obj.get("repair_hints", {})
    if isinstance(repair_hints, dict):
        path = repair_hints.get("enrichment_path", "")
        if isinstance(path, str) and path.strip():
            return path.strip()
    return "docs/demo/world_enrich.json"


def _recommended_focus_inputs(base_output: dict, output_obj: dict) -> dict:
    params = output_obj.get("casefile", {}).get("query", "")
    if isinstance(params, str) and params:
        query = params
    else:
        query = output_obj.get("verification_result", {}).get("target_claim_id", "")

    max_chunks_raw = output_obj.get("casefile", {}).get("input", {}).get(
        "max_chunks",
        None,
    )
    if not isinstance(max_chunks_raw, int):
        max_chunks_raw = base_output.get("__bundle_params", {}).get("max_chunks", None)
    if isinstance(max_chunks_raw, int):
        recommended_max_chunks = min(40, max_chunks_raw + 10)
    else:
        recommended_max_chunks = 30
    return {
        "recommended_max_chunks": recommended_max_chunks,
        "recommended_max_events": 30,
        "recommended_query": str(query),
    }


def compute_repair_plan(base_output: dict, ruleset_id: str) -> dict:
    output_obj = _extract_output_obj(base_output)
    verification_result = output_obj["verification_result"]
    status = verification_result["status"]
    reason_codes = sorted(
        {
            reason["code"]
            for reason in verification_result.get("reasons", [])
            if isinstance(reason.get("code"), str)
        }
    )

    actions = []

    if status == "VERIFIED_NEEDS_INFO":
        missing = []
        for item in verification_result.get("required_info", []):
            kind = item.get("kind")
            event_id = item.get("ref", {}).get("event_id")
            if kind not in {"missing_time", "missing_actor", "missing_object"}:
                continue
            if not isinstance(event_id, str):
                continue
            missing.append({"kind": kind, "event_id": event_id, "value": None})
        missing = sorted(missing, key=lambda item: (item["kind"], item["event_id"]))

        needs_unknown_security = "RULE_WORLD_UNKNOWNS_SECURITY" in reason_codes
        has_missing_required = bool(missing)
        if needs_unknown_security or has_missing_required:
            actions.append(
                {
                    "action_id": "",
                    "kind": "ADD_WORLD_ENRICHMENT",
                    "risk": "low",
                    "priority": 10,
                    "goal": "Fill missing world context required for verification.",
                    "inputs": {
                        "enrichment_path": _default_enrichment_path(output_obj),
                        "missing": missing,
                    },
                    "expected_effect": {
                        "clears_reasons": [
                            code
                            for code in [
                                "RULE_WORLD_UNKNOWNS_SECURITY",
                                "RULE_CAUSAL_NEEDS_INFO",
                            ]
                            if code in reason_codes
                        ],
                        "may_change_hashes": True,
                    },
                    "receipts": {
                        "trigger_reasons": reason_codes,
                        "event_ids": sorted(
                            {
                                item["event_id"]
                                for item in missing
                                if isinstance(item["event_id"], str)
                            }
                        ),
                        "entity_ids": _collect_entity_ids_from_verification(
                            verification_result
                        ),
                        "evidence_refs": _collect_evidence_refs(verification_result),
                    },
                }
            )

    if status == "VERIFIED_FAIL" and "RULE_CONSTRAINT_VIOLATION" in reason_codes:
        involved_event_ids = _collect_event_ids_from_verification(verification_result)
        involved_entity_ids = _collect_entity_ids_from_verification(verification_result)
        actions.append(
            {
                "action_id": "",
                "kind": "APPLY_WORLD_PATCH",
                "risk": "high",
                "priority": 20,
                "goal": "Address constraint violation(s) in world state.",
                "inputs": {
                    "patch_path": "docs/demo/world_patch.json",
                    "description": (
                        "Remove or adjust violating event(s); "
                        "see constraint_report.violations[]."
                    ),
                },
                "expected_effect": {
                    "clears_reasons": ["RULE_CONSTRAINT_VIOLATION"],
                    "may_change_hashes": True,
                },
                "receipts": {
                    "trigger_reasons": ["RULE_CONSTRAINT_VIOLATION"],
                    "event_ids": involved_event_ids,
                    "entity_ids": involved_entity_ids,
                    "evidence_refs": _collect_evidence_refs(verification_result),
                },
            }
        )

    if status == "VERIFIED_FAIL" and "RULE_CAUSAL_TEMPORAL_CYCLE" in reason_codes:
        cycle_event_ids = _collect_event_ids_from_verification(verification_result)
        actions.append(
            {
                "action_id": "",
                "kind": "APPLY_WORLD_PATCH",
                "risk": "high",
                "priority": 25,
                "goal": "Break causal temporal cycle by adjusting or removing events.",
                "inputs": {
                    "patch_path": "docs/demo/world_patch_cycle_fix.json",
                    "description": (
                        "Adjust time ordering or remove an event in the cycle "
                        "participants."
                    ),
                },
                "expected_effect": {
                    "clears_reasons": ["RULE_CAUSAL_TEMPORAL_CYCLE"],
                    "may_change_hashes": True,
                },
                "receipts": {
                    "trigger_reasons": ["RULE_CAUSAL_TEMPORAL_CYCLE"],
                    "event_ids": cycle_event_ids,
                    "entity_ids": _collect_entity_ids_from_verification(
                        verification_result
                    ),
                    "evidence_refs": _collect_evidence_refs(verification_result),
                },
            }
        )

    if status == "VERIFIED_FAIL" and "RULE_SCOPE" in reason_codes:
        actions.append(
            {
                "action_id": "",
                "kind": "TUNE_FOCUS",
                "risk": "medium",
                "priority": 30,
                "goal": "Tune retrieval scope to keep verification evidence in-bounds.",
                "inputs": _recommended_focus_inputs(base_output, output_obj),
                "expected_effect": {
                    "clears_reasons": ["RULE_SCOPE"],
                    "may_change_hashes": True,
                },
                "receipts": {
                    "trigger_reasons": ["RULE_SCOPE"],
                    "event_ids": _collect_event_ids_from_verification(
                        verification_result
                    ),
                    "entity_ids": _collect_entity_ids_from_verification(
                        verification_result
                    ),
                    "evidence_refs": _collect_evidence_refs(verification_result),
                },
            }
        )

    for action in actions:
        action["action_id"] = _action_id(action)

    actions = sorted(
        actions,
        key=lambda item: (
            item["priority"],
            _RISK_ORDER[item["risk"]],
            item["action_id"],
        ),
    )

    plan = {
        "version": "1.0",
        "plan_id": "",
        "base": _base_hashes(base_output, output_obj),
        "status": status,
        "actions": actions,
        "notes": "Deterministic repair planning; no autonomous external actions.",
        "ruleset_id": ruleset_id,
    }
    plan["plan_id"] = _plan_id(plan)

    validate(plan, "schemas/repair_plan.schema.json")
    return plan


def repair_out_dir_name(plan_id: str) -> str:
    return plan_id.replace(":", "_")


def default_out_dir(base_out_dir: str, plan_id: str) -> Path:
    return Path(base_out_dir) / repair_out_dir_name(plan_id)
