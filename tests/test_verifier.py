from pathlib import Path

from core.reasoning.verifier import load_ruleset, verify_claim


def _bundle_with_artifact(
    *,
    source_id: str = "doc:1",
    chunk_id: str = "chunk:1",
) -> dict:
    return {
        "bundle_version": "1.0",
        "created_utc": "2026-03-01T12:00:00Z",
        "inputs": {
            "prompt": "verify",
            "params": {},
        },
        "artifacts": [
            {
                "source_id": source_id,
                "chunk_id": chunk_id,
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


def _evidence_ref(*, source_id: str = "doc:1", chunk_id: str = "chunk:1") -> dict:
    return {
        "source_id": source_id,
        "chunk_id": chunk_id,
        "offset_start": 0,
        "offset_end": 10,
        "text_sha256": (
            "ee8250fb76e094b34b471f13a73dbbe51d1ae142e9df59d7c0d31ec20f0a0a8e"
        ),
    }


def test_verify_claim_ok_with_evidence_and_no_conflicts():
    result = verify_claim(
        ruleset_id="ruleset.core.v1",
        target_claim_id="C",
        evidence_bundle_obj=_bundle_with_artifact(),
        sealed_output_obj={
            "findings": {"contradictions": []},
            "support_tree": {
                "target_claim_id": "C",
                "nodes": [
                    {
                        "claim_id": "C",
                        "claim": {
                            "evidence": [_evidence_ref()],
                        },
                    }
                ],
                "edges": [],
            },
        },
    )

    assert result["status"] == "VERIFIED_OK"
    assert result["reasons"] == []
    assert result["required_info"] == []
    assert result["receipts"]["ruleset_sha256"]


def test_verify_claim_fails_on_contradiction():
    result = verify_claim(
        ruleset_id="ruleset.core.v1",
        target_claim_id="C",
        evidence_bundle_obj=_bundle_with_artifact(),
        sealed_output_obj={
            "findings": {
                "contradictions": [
                    {
                        "claim_a": "A",
                        "claim_b": "C",
                        "reason": "conflict",
                    }
                ]
            },
            "support_tree": {
                "target_claim_id": "C",
                "nodes": [
                    {
                        "claim_id": "C",
                        "claim": {
                            "evidence": [_evidence_ref()],
                        },
                    }
                ],
                "edges": [],
            },
        },
    )

    assert result["status"] == "VERIFIED_FAIL"
    assert result["reasons"][0]["code"] == "RULE_CONTRADICTION"


def test_verify_claim_needs_info_for_security_world_unknowns():
    result = verify_claim(
        ruleset_id="ruleset.core.v1",
        target_claim_id="world:test",
        evidence_bundle_obj=_bundle_with_artifact(),
        sealed_output_obj={
            "world_model": {
                "world_version": "1.0",
                "world_sha256": "a" * 64,
                "entities": [],
                "events": [
                    {
                        "event_id": "event:1",
                        "type": "Config",
                        "time": {"kind": "unknown"},
                        "actors": [],
                        "objects": [],
                        "action": "API key access was granted",
                        "state": None,
                        "evidence": [_evidence_ref()],
                    }
                ],
                "relations": [],
                "unknowns": [
                    {
                        "kind": "missing_time",
                        "ref": {"event_id": "event:1"},
                    }
                ],
                "conflicts": [],
            }
        },
    )

    assert result["status"] == "VERIFIED_NEEDS_INFO"
    assert result["reasons"][0]["code"] == "RULE_WORLD_UNKNOWNS_SECURITY"
    assert result["required_info"] == [
        {
            "kind": "missing_time",
            "ref": {"event_id": "event:1"},
        }
    ]


def test_verify_claim_fails_when_evidence_scope_is_outside_bundle():
    result = verify_claim(
        ruleset_id="ruleset.core.v1",
        target_claim_id="C",
        evidence_bundle_obj=_bundle_with_artifact(),
        sealed_output_obj={
            "findings": {"contradictions": []},
            "support_tree": {
                "target_claim_id": "C",
                "nodes": [
                    {
                        "claim_id": "C",
                        "claim": {
                            "evidence": [_evidence_ref(source_id="doc:2")],
                        },
                    }
                ],
                "edges": [],
            },
        },
    )

    assert result["status"] == "VERIFIED_FAIL"
    assert result["reasons"][0]["code"] == "RULE_SCOPE"


def test_verifier_ruleset_loading_by_id_and_path_is_deterministic():
    by_id, by_id_sha = load_ruleset("ruleset.core.v1")
    by_path, by_path_sha = load_ruleset(
        str(Path("rulesets") / "ruleset.core.v1.json")
    )

    assert by_id == by_path
    assert by_id_sha == by_path_sha
    assert by_id["ruleset_id"] == "ruleset.core.v1"


def test_ruleset_hash_recorded():
    ruleset_obj, ruleset_sha = load_ruleset("ruleset.core.v1")
    result = verify_claim(
        ruleset_id=str(Path("rulesets") / "ruleset.core.v1.json"),
        target_claim_id="C",
        evidence_bundle_obj=_bundle_with_artifact(),
        sealed_output_obj={
            "findings": {"contradictions": []},
            "support_tree": {
                "target_claim_id": "C",
                "nodes": [
                    {
                        "claim_id": "C",
                        "claim": {
                            "evidence": [_evidence_ref()],
                        },
                    }
                ],
                "edges": [],
            },
        },
    )

    assert ruleset_obj["ruleset_id"] == result["ruleset_id"]
    assert result["receipts"]["ruleset_sha256"] == ruleset_sha


def test_verifier_dedup():
    result = verify_claim(
        ruleset_id="ruleset.core.v1",
        target_claim_id="world:test",
        evidence_bundle_obj=_bundle_with_artifact(),
        sealed_output_obj={
            "world_model": {
                "world_version": "1.0",
                "world_sha256": "a" * 64,
                "entities": [],
                "events": [
                    {
                        "event_id": "event:1",
                        "type": "Config",
                        "time": {"kind": "unknown"},
                        "actors": [],
                        "objects": [],
                        "action": "API key access was granted",
                        "state": None,
                        "evidence": [_evidence_ref()],
                    },
                    {
                        "event_id": "event:1",
                        "type": "Config",
                        "time": {"kind": "unknown"},
                        "actors": [],
                        "objects": [],
                        "action": "API key access was granted",
                        "state": None,
                        "evidence": [_evidence_ref()],
                    },
                ],
                "relations": [],
                "unknowns": [
                    {"kind": "missing_time", "ref": {"event_id": "event:1"}},
                    {"kind": "missing_time", "ref": {"event_id": "event:1"}},
                ],
                "conflicts": [],
            }
        },
    )

    assert result["reasons"] == [
        {
            "code": "RULE_WORLD_UNKNOWNS_SECURITY",
            "message": "security-relevant world event is missing required context",
            "ref": {"event_id": "event:1"},
        }
    ]
    assert result["required_info"] == [
        {"kind": "missing_time", "ref": {"event_id": "event:1"}}
    ]


def test_verify_claim_needs_info_for_security_causal_unknowns():
    result = verify_claim(
        ruleset_id="ruleset.core.v1",
        target_claim_id="world:test",
        evidence_bundle_obj=_bundle_with_artifact(),
        sealed_output_obj={
            "world_model": {
                "world_version": "1.0",
                "world_sha256": "a" * 64,
                "entities": [],
                "events": [
                    {
                        "event_id": "event:1",
                        "type": "Config",
                        "time": {"kind": "unknown"},
                        "actors": [],
                        "objects": [],
                        "action": "API key config was updated",
                        "state": None,
                        "evidence": [_evidence_ref()],
                    }
                ],
                "relations": [],
                "unknowns": [],
                "conflicts": [],
            },
            "causal_graph": {
                "version": "1.0",
                "nodes": [],
                "edges": [],
                "causal_order": [],
                "findings": [
                    {
                        "code": "UNKNOWN_BLOCKS_CAUSAL",
                        "message": "missing object blocks causal inference",
                        "event_ids": ["event:1"],
                        "details": {
                            "missing_kinds": ["missing_object"],
                            "reason_code": "RULE_POLICY_PRECEDES_CONFIG",
                        },
                    }
                ],
            },
        },
    )

    assert result["status"] == "VERIFIED_NEEDS_INFO"
    assert result["reasons"] == [
        {
            "code": "RULE_CAUSAL_NEEDS_INFO",
            "message": (
                "security-relevant causal inference is blocked by missing "
                "required context"
            ),
            "ref": {"event_id": "event:1"},
        }
    ]
    assert result["required_info"] == [
        {"kind": "missing_object", "ref": {"event_id": "event:1"}}
    ]
