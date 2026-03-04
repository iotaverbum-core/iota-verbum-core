import json
from pathlib import Path

from core.reasoning.constraints import compute_constraints
from core.reasoning.verifier import verify_claim

FIXTURES = Path("tests/fixtures")


def _fixture() -> dict:
    return json.loads(
        (FIXTURES / "constraint_world_example.json").read_text(encoding="utf-8")
    )


def _bundle() -> dict:
    return {
        "bundle_version": "1.0",
        "created_utc": "2026-03-01T12:00:00Z",
        "inputs": {"prompt": "verify", "params": {}},
        "artifacts": [
            {
                "source_id": "doc:1",
                "chunk_id": "chunk:1",
                "offset_start": 0,
                "offset_end": 10,
                "text": "evidence",
                "text_sha256": (
                    "ee8250fb76e094b34b471f13a73dbbe51d1ae142e9df59d7c0d31ec20f0a0a8e"
                ),
            }
        ],
        "toolchain": {
            "core_version": "0.3.0",
            "parser_versions": {},
            "schema_versions": {
                "attestation_record": "1.0",
                "evidence_bundle": "1.0",
                "evidence_pack": "1.0",
            },
        },
        "policy": {"ruleset_id": "ruleset.core.v1"},
    }


def test_compute_constraints_matches_fixture_deterministically():
    fixture = _fixture()
    first = compute_constraints(fixture["world_model"], fixture["causal_graph"])
    second = compute_constraints(fixture["world_model"], fixture["causal_graph"])
    expected = json.loads(
        (FIXTURES / "constraint_expected.json").read_text(encoding="utf-8")
    )

    assert first == second
    assert first == expected


def test_verify_claim_fails_when_constraint_report_has_violations():
    fixture = _fixture()
    constraint_report = compute_constraints(
        fixture["world_model"],
        fixture["causal_graph"],
    )
    result = verify_claim(
        ruleset_id="ruleset.core.v1",
        target_claim_id="world:test",
        evidence_bundle_obj=_bundle(),
        sealed_output_obj={
            "world_model": fixture["world_model"],
            "causal_graph": fixture["causal_graph"],
            "constraint_report": constraint_report,
        },
    )

    assert result["status"] == "VERIFIED_FAIL"
    assert result["reasons"][0]["code"] == "RULE_CONSTRAINT_VIOLATION"
