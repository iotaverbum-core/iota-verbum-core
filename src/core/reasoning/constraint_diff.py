from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate
from core.reasoning.world_diff import load_output_input


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _unwrap_output_and_meta(raw_output: dict) -> tuple[dict, dict]:
    if "output" in raw_output and isinstance(raw_output["output"], dict):
        return raw_output["output"], raw_output.get("__meta__", {})
    return raw_output, raw_output.get("__meta__", {})


def _extract_constraint_report(raw_output: dict) -> tuple[dict, dict]:
    output_obj, meta = _unwrap_output_and_meta(raw_output)
    if "constraint_report" in output_obj:
        report = output_obj["constraint_report"]
    elif "output" in output_obj and "constraint_report" in output_obj["output"]:
        report = output_obj["output"]["constraint_report"]
    else:
        raise ValueError("sealed output missing constraint_report")
    validate(report, "schemas/constraint_report.schema.json")
    return report, meta


def _extract_verification_result(raw_output: dict) -> dict:
    output_obj, _meta = _unwrap_output_and_meta(raw_output)
    if "verification_result" in output_obj:
        return output_obj["verification_result"]
    if "output" in output_obj and "verification_result" in output_obj["output"]:
        return output_obj["output"]["verification_result"]
    raise ValueError("sealed output missing verification_result")


def _extract_world_sha256(raw_output: dict) -> str:
    output_obj, _meta = _unwrap_output_and_meta(raw_output)
    if "world_model" in output_obj:
        return output_obj["world_model"]["world_sha256"]
    if "output" in output_obj and "world_model" in output_obj["output"]:
        return output_obj["output"]["world_model"]["world_sha256"]
    raise ValueError("sealed output missing world_model")


def _hash_meta(raw_output: dict, meta: dict) -> dict:
    output_obj, _ = _unwrap_output_and_meta(raw_output)
    output_sha256 = meta.get("output_sha256")
    if output_sha256 is None:
        output_sha256 = sha256_bytes(dumps_canonical(output_obj))
    return {
        "output_sha256": output_sha256,
        "world_sha256": _extract_world_sha256(raw_output),
        "attestation_sha256": meta.get("attestation_sha256", ""),
    }


def _violation_fingerprint(violation: dict) -> str:
    key = {
        "type": violation["type"],
        "events": sorted(violation["events"]),
        "entities": sorted(violation["entities"]),
        "reason": violation["reason"],
    }
    return sha256_bytes(dumps_canonical(key))


def _violation_identity_key(
    violation: dict,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return (
        violation["type"],
        tuple(sorted(violation["events"])),
        tuple(sorted(violation["entities"])),
    )


def _sort_violation(
    violation: dict,
) -> tuple[str, tuple[str, ...], tuple[str, ...], str, str]:
    return (
        violation["type"],
        tuple(violation["events"]),
        tuple(violation["entities"]),
        violation["reason"],
        _sort_key({"evidence": violation["evidence"]}),
    )


def _sort_changed(change: dict) -> tuple:
    return (
        change["new"]["type"],
        tuple(change["new"]["events"]),
        tuple(change["new"]["entities"]),
        change["old"]["reason"],
        change["new"]["reason"],
    )


def compute_constraint_diff(*, old_output: dict, new_output: dict) -> dict:
    old_report, old_meta = _extract_constraint_report(old_output)
    new_report, new_meta = _extract_constraint_report(new_output)
    old_verification = _extract_verification_result(old_output)
    new_verification = _extract_verification_result(new_output)

    old_by_fingerprint = {
        _violation_fingerprint(violation): violation
        for violation in old_report["violations"]
    }
    new_by_fingerprint = {
        _violation_fingerprint(violation): violation
        for violation in new_report["violations"]
    }
    unchanged_fingerprints = set(old_by_fingerprint) & set(new_by_fingerprint)

    old_remaining = [
        violation
        for fingerprint, violation in old_by_fingerprint.items()
        if fingerprint not in unchanged_fingerprints
    ]
    new_remaining = [
        violation
        for fingerprint, violation in new_by_fingerprint.items()
        if fingerprint not in unchanged_fingerprints
    ]

    old_by_identity = {
        _violation_identity_key(violation): violation for violation in old_remaining
    }
    new_by_identity = {
        _violation_identity_key(violation): violation for violation in new_remaining
    }
    changed_keys = set(old_by_identity) & set(new_by_identity)

    changed = [
        {
            "old": old_by_identity[key],
            "new": new_by_identity[key],
        }
        for key in sorted(changed_keys)
    ]

    removed = [
        violation
        for key, violation in old_by_identity.items()
        if key not in changed_keys
    ]
    added = [
        violation
        for key, violation in new_by_identity.items()
        if key not in changed_keys
    ]

    diff = {
        "version": "1.0",
        "old": _hash_meta(old_output, old_meta),
        "new": _hash_meta(new_output, new_meta),
        "verification_change": {
            "old": old_verification["status"],
            "new": new_verification["status"],
        },
        "violations": {
            "added": sorted(added, key=_sort_violation),
            "removed": sorted(removed, key=_sort_violation),
            "changed": sorted(changed, key=_sort_changed),
        },
        "counts": {
            "old_total": len(old_report["violations"]),
            "new_total": len(new_report["violations"]),
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
    }
    validate(diff, "schemas/constraint_diff.schema.json")
    return diff


def load_constraint_diff_input(path: str) -> dict:
    return load_output_input(path)
