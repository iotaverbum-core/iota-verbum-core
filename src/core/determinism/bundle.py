from __future__ import annotations

from copy import deepcopy

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes, sha256_text
from core.determinism.schema_validate import validate


def build_evidence_bundle(
    bundle_obj: dict,
    schema_path: str = "schemas/evidence_bundle.schema.json",
) -> tuple[bytes, str]:
    bundle = deepcopy(bundle_obj)
    for artifact in bundle.get("artifacts", []):
        computed_sha = sha256_text(artifact["text"])
        recorded_sha = artifact.get("text_sha256")
        if recorded_sha is None:
            artifact["text_sha256"] = computed_sha
        elif recorded_sha != computed_sha:
            raise ValueError("artifact text_sha256 mismatch")

    validate(bundle, schema_path)
    bundle_bytes = dumps_canonical(bundle)
    return bundle_bytes, sha256_bytes(bundle_bytes)
