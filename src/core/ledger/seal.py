from __future__ import annotations

from core.ledger.hash import hash_artifact
from core.ledger.manifest import build_manifest


def seal_run(stages: dict[str, dict], run_config: dict) -> dict:
    manifest = build_manifest(stages, run_config)
    return {
        "manifest": manifest,
        "bundle_sha256": hash_artifact({"manifest": manifest, "stages": stages}),
    }
