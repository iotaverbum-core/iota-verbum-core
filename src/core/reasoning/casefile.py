from __future__ import annotations

from copy import deepcopy

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate

_ROLE_ORDER = {
    "sealed": 0,
    "derived": 1,
    "narrative": 2,
}
_UNKNOWN_SHA256 = "0" * 64


def _sha256_of_lf_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return sha256_bytes(normalized.encode("utf-8"))


def _artifacts_sort_key(item: dict) -> tuple[int, str]:
    return (_ROLE_ORDER[item["role"]], item["name"])


def _add_artifact(
    artifacts: list[dict],
    *,
    name: str,
    role: str,
    sha256: str,
    schema: str = "",
    notes: str = "",
) -> None:
    artifact = {"name": name, "role": role, "sha256": sha256}
    if schema:
        artifact["schema"] = schema
    if notes:
        artifact["notes"] = notes
    artifacts.append(artifact)


def _casefile_for_id_hash(casefile_obj: dict) -> dict:
    hashed = deepcopy(casefile_obj)
    hashed["casefile_id"] = ""
    hashed["hashes"]["output_sha256"] = _UNKNOWN_SHA256
    hashed["hashes"]["attestation_sha256"] = _UNKNOWN_SHA256
    for artifact in hashed["artifacts"]:
        if artifact["name"] in {"output.json", "attestation.json", "casefile.json"}:
            artifact["sha256"] = _UNKNOWN_SHA256
    return hashed


def _casefile_for_artifact_hash(casefile_obj: dict) -> dict:
    hashed = deepcopy(casefile_obj)
    hashed["hashes"]["output_sha256"] = _UNKNOWN_SHA256
    hashed["hashes"]["attestation_sha256"] = _UNKNOWN_SHA256
    for artifact in hashed["artifacts"]:
        if artifact["name"] in {"output.json", "attestation.json", "casefile.json"}:
            artifact["sha256"] = _UNKNOWN_SHA256
    return hashed


def casefile_artifact_sha256(casefile_obj: dict) -> str:
    artifact = next(
        item for item in casefile_obj["artifacts"] if item["name"] == "casefile.json"
    )
    return artifact["sha256"]


def build_casefile(
    *,
    output_obj: dict,
    query: str,
    prompt: str,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    manifest_sha256: str,
    ledger_dir_rel: str,
    bundle_sha256: str,
    output_sha256: str,
    attestation_sha256: str,
) -> dict:
    world_model = output_obj.get("world_model", {})
    verification_result = output_obj.get("verification_result", {})
    receipts = verification_result.get("receipts", {})
    constraint_report = output_obj.get("constraint_report", {})
    causal_graph = output_obj.get("causal_graph", {})
    artifacts: list[dict] = []

    _add_artifact(
        artifacts,
        name="attestation.json",
        role="sealed",
        sha256=attestation_sha256,
        schema="schemas/attestation_record.schema.json",
    )
    _add_artifact(
        artifacts,
        name="bundle.json",
        role="sealed",
        sha256=bundle_sha256,
        schema="schemas/evidence_bundle.schema.json",
    )
    _add_artifact(
        artifacts,
        name="output.json",
        role="sealed",
        sha256=output_sha256,
    )

    if "world_narrative_v2" in output_obj:
        _add_artifact(
            artifacts,
            name="world_narrative_v2.txt",
            role="narrative",
            sha256=_sha256_of_lf_text(output_obj["world_narrative_v2"]["text"]),
            schema="schemas/world_narrative_v2.schema.json",
        )
    if "constraint_narrative_v2" in output_obj:
        _add_artifact(
            artifacts,
            name="constraint_narrative_v2.txt",
            role="narrative",
            sha256=_sha256_of_lf_text(output_obj["constraint_narrative_v2"]["text"]),
            schema="schemas/constraint_narrative_v2.schema.json",
        )
    if "causal_narrative_v2" in output_obj:
        _add_artifact(
            artifacts,
            name="causal_narrative_v2.txt",
            role="narrative",
            sha256=_sha256_of_lf_text(output_obj["causal_narrative_v2"]["text"]),
            schema="schemas/causal_narrative_v2.schema.json",
        )

    optional_derived = {
        "world_diff": ("world_diff.json", "schemas/world_diff.schema.json"),
        "constraint_diff": (
            "constraint_diff.json",
            "schemas/constraint_diff.schema.json",
        ),
        "world_patch": ("world_patch.json", "schemas/world_patch.schema.json"),
        "world_patch_result": (
            "world_patch_result.json",
            "schemas/world_patch_result.schema.json",
        ),
    }
    for key, (name, schema) in sorted(optional_derived.items()):
        if key in output_obj:
            _add_artifact(
                artifacts,
                name=name,
                role="derived",
                sha256=sha256_bytes(dumps_canonical(output_obj[key])),
                schema=schema,
            )

    _add_artifact(
        artifacts,
        name="casefile.json",
        role="derived",
        sha256=_UNKNOWN_SHA256,
        schema="schemas/casefile.schema.json",
        notes=(
            "sha256 preimage excludes hashes.output_sha256 and "
            "hashes.attestation_sha256 to avoid sealing cycles"
        ),
    )
    artifacts = sorted(artifacts, key=_artifacts_sort_key)

    casefile = {
        "casefile_version": "1.0",
        "casefile_id": "",
        "created_utc": created_utc,
        "core_version": core_version,
        "ruleset_id": ruleset_id,
        "query": query,
        "prompt": prompt,
        "hashes": {
            "manifest_sha256": manifest_sha256,
            "bundle_sha256": bundle_sha256,
            "world_sha256": world_model.get("world_sha256", _UNKNOWN_SHA256),
            "output_sha256": output_sha256,
            "attestation_sha256": attestation_sha256,
        },
        "ledger_dir": ledger_dir_rel,
        "summary": {
            "entities": len(world_model.get("entities", [])),
            "events": len(world_model.get("events", [])),
            "unknowns": len(world_model.get("unknowns", [])),
            "conflicts": len(world_model.get("conflicts", [])),
            "verification_status": verification_result.get(
                "status",
                "VERIFIED_NEEDS_INFO",
            ),
            "constraint_violations": len(constraint_report.get("violations", [])),
            "causal_edges": len(causal_graph.get("edges", [])),
        },
        "artifacts": artifacts,
        "receipts_summary": {
            "evidence_ref_count": len(receipts.get("evidence_refs", [])),
            "proof_count": len(receipts.get("proofs", [])),
            "finding_count": len(receipts.get("findings", [])),
        },
    }
    casefile_id = "case:" + sha256_bytes(
        dumps_canonical(_casefile_for_id_hash(casefile))
    )
    casefile["casefile_id"] = casefile_id
    casefile_sha = sha256_bytes(dumps_canonical(_casefile_for_artifact_hash(casefile)))
    for artifact in casefile["artifacts"]:
        if artifact["name"] == "casefile.json":
            artifact["sha256"] = casefile_sha
            break
    casefile["artifacts"] = sorted(casefile["artifacts"], key=_artifacts_sort_key)
    validate(casefile, "schemas/casefile.schema.json")
    return casefile
