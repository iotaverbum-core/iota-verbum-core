from __future__ import annotations

from copy import deepcopy

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate


def build_attestation(
    att_obj: dict,
    output_bytes: bytes,
    schema_path: str = "schemas/attestation_record.schema.json",
) -> tuple[bytes, str]:
    attestation = deepcopy(att_obj)
    computed_output_sha = sha256_bytes(output_bytes)
    recorded_output_sha = attestation.get("output_sha256")
    if recorded_output_sha is None:
        attestation["output_sha256"] = computed_output_sha
    elif recorded_output_sha != computed_output_sha:
        raise ValueError("attestation output_sha256 mismatch")

    validate(attestation, schema_path)
    attestation_bytes = dumps_canonical(attestation)
    return attestation_bytes, sha256_bytes(attestation_bytes)
