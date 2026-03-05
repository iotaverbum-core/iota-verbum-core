from core.reasoning.verifier import verify_claim


def _bundle() -> dict:
    return {
        "bundle_version": "1.0",
        "created_utc": "2026-03-01T12:00:00Z",
        "inputs": {
            "prompt": "verify",
            "params": {},
        },
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
        "policy": {
            "ruleset_id": "ruleset.core.v1",
        },
    }


def test_verify_claim_fails_on_causal_temporal_cycle():
    result = verify_claim(
        ruleset_id="ruleset.core.v1",
        target_claim_id="world:test",
        evidence_bundle_obj=_bundle(),
        sealed_output_obj={
            "world_model": {
                "world_version": "1.0",
                "world_sha256": "a" * 64,
                "entities": [],
                "events": [],
                "relations": [],
                "unknowns": [],
                "conflicts": [],
            },
            "causal_graph": {
                "version": "1.0",
                "nodes": [
                    "event:" + ("1" * 64),
                    "event:" + ("2" * 64),
                ],
                "edges": [],
                "causal_order": [],
                "findings": [
                    {
                        "code": "CYCLE_TEMPORAL_CONSTRAINT",
                        "message": "Temporal before edges contain a cycle",
                        "event_ids": [
                            "event:" + ("1" * 64),
                            "event:" + ("2" * 64),
                        ],
                        "details": {"edge_count": 2},
                    }
                ],
            },
        },
    )

    assert result["status"] == "VERIFIED_FAIL"
    assert result["reasons"] == [
        {
            "code": "RULE_CAUSAL_TEMPORAL_CYCLE",
            "message": "causal temporal constraints contain a cycle",
            "ref": {
                "event_ids": [
                    "event:" + ("1" * 64),
                    "event:" + ("2" * 64),
                ]
            },
        }
    ]
