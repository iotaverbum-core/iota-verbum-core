from __future__ import annotations

from core.determinism.attest import build_attestation
from core.determinism.bundle import build_evidence_bundle
from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes


def canonicalize_output(output_obj: object) -> bytes:
    return dumps_canonical(output_obj)


def finalize(
    evidence_bundle_obj: dict,
    output_obj: object,
    *,
    manifest_sha256: str,
    core_version: str,
    ruleset_id: str,
    created_utc: str,
    bundle_version: str = "1.0",
    attestation_version: str = "1.0",
) -> dict:
    try:
        bundle_schema_version = evidence_bundle_obj["toolchain"]["schema_versions"][
            "evidence_bundle"
        ]
        attestation_schema_version = evidence_bundle_obj["toolchain"][
            "schema_versions"
        ]["attestation_record"]
    except KeyError as exc:
        raise ValueError(
            "evidence bundle missing required schema version fields"
        ) from exc

    if evidence_bundle_obj.get("bundle_version") != bundle_version:
        raise ValueError("evidence bundle_version does not match finalize request")
    if bundle_schema_version != bundle_version:
        raise ValueError("evidence bundle schema version does not match bundle_version")
    if attestation_schema_version != attestation_version:
        raise ValueError(
            "evidence bundle attestation schema version does not match "
            "attestation_version"
        )

    bundle_bytes, bundle_sha256 = build_evidence_bundle(evidence_bundle_obj)
    output_bytes = canonicalize_output(output_obj)
    output_sha256 = sha256_bytes(output_bytes)

    attestation_obj = {
        "attestation_version": attestation_version,
        "created_utc": created_utc,
        "bundle_sha256": bundle_sha256,
        "core_version": core_version,
        "ruleset_id": ruleset_id,
        "manifest_sha256": manifest_sha256,
        "output_sha256": output_sha256,
    }
    attestation_bytes, attestation_sha256 = build_attestation(
        attestation_obj,
        output_bytes,
    )

    return {
        "bundle_bytes": bundle_bytes,
        "bundle_sha256": bundle_sha256,
        "output_bytes": output_bytes,
        "output_sha256": output_sha256,
        "attestation_bytes": attestation_bytes,
        "attestation_sha256": attestation_sha256,
    }
