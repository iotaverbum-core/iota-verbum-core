from __future__ import annotations

from core.determinism.schema_validate import validate
from core.ledger.hash import hash_artifact


def build_manifest(stages: dict[str, dict], run_config: dict) -> dict:
    stage_hashes = {
        name: hash_artifact(payload) for name, payload in sorted(stages.items())
    }
    manifest = {
        "schema_version": "2.0",
        "stable_timestamp_policy": "provided_by_input_config",
        "run_config": run_config,
        "stage_hashes": stage_hashes,
    }
    validate(manifest, "schemas/ledger_manifest_v2.schema.json")
    return manifest
