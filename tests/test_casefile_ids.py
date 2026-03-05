import json
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.reasoning.casefile import build_casefile, casefile_artifact_sha256

FIXTURES = Path("tests/fixtures")


def _base_output() -> dict:
    return json.loads(
        (FIXTURES / "counterfactual_base_output.json").read_text(encoding="utf-8")
    )


def test_casefile_id_is_stable_when_output_and_attestation_hashes_change():
    output_obj = _base_output()
    first = build_casefile(
        output_obj=output_obj,
        query="q",
        prompt="p",
        created_utc="2026-03-05T00:00:00Z",
        core_version="0.4.0",
        ruleset_id="ruleset.core.v1",
        manifest_sha256="1" * 64,
        ledger_dir_rel="outputs/demo/run/ledger/" + ("a" * 64),
        bundle_sha256="a" * 64,
        output_sha256="b" * 64,
        attestation_sha256="c" * 64,
    )
    second = build_casefile(
        output_obj=output_obj,
        query="q",
        prompt="p",
        created_utc="2026-03-05T00:00:00Z",
        core_version="0.4.0",
        ruleset_id="ruleset.core.v1",
        manifest_sha256="1" * 64,
        ledger_dir_rel="outputs/demo/run/ledger/" + ("a" * 64),
        bundle_sha256="a" * 64,
        output_sha256="d" * 64,
        attestation_sha256="e" * 64,
    )

    assert first["casefile_id"] == second["casefile_id"]
    assert casefile_artifact_sha256(first) == casefile_artifact_sha256(second)


def test_casefile_canonicalization_is_idempotent():
    output_obj = _base_output()
    first = build_casefile(
        output_obj=output_obj,
        query="timeline",
        prompt="prompt",
        created_utc="2026-03-05T00:00:00Z",
        core_version="0.4.0",
        ruleset_id="ruleset.core.v1",
        manifest_sha256="1" * 64,
        ledger_dir_rel="outputs/demo/run/ledger/" + ("a" * 64),
        bundle_sha256="a" * 64,
        output_sha256="b" * 64,
        attestation_sha256="c" * 64,
    )
    first_bytes = dumps_canonical(first)
    rebuilt = json.loads(first_bytes.decode("utf-8"))
    second = build_casefile(
        output_obj=output_obj,
        query=rebuilt["query"],
        prompt=rebuilt["prompt"],
        created_utc=rebuilt["created_utc"],
        core_version=rebuilt["core_version"],
        ruleset_id=rebuilt["ruleset_id"],
        manifest_sha256=rebuilt["hashes"]["manifest_sha256"],
        ledger_dir_rel=rebuilt["ledger_dir"],
        bundle_sha256=rebuilt["hashes"]["bundle_sha256"],
        output_sha256=rebuilt["hashes"]["output_sha256"],
        attestation_sha256=rebuilt["hashes"]["attestation_sha256"],
    )
    second_bytes = dumps_canonical(second)

    assert first_bytes == second_bytes
