import json
from pathlib import Path

from core.reasoning.world_diff import compute_world_diff

FIXTURES = Path("tests/fixtures")


def _wrapped_output(
    *,
    world_sha256: str,
    output_sha256: str,
    attestation_sha256: str,
    events: list[dict],
    unknowns: list[dict],
    verification_status: str,
    reasons: list[dict],
    required_info: list[dict],
) -> dict:
    return {
        "output": {
            "world_model": {
                "world_version": "1.0",
                "world_sha256": world_sha256,
                "entities": [
                    {
                        "entity_id": "entity:shared",
                        "type": "Concept",
                        "name": "Shared",
                        "aliases": [],
                    },
                    *(
                        [
                            {
                                "entity_id": "entity:new",
                                "type": "Concept",
                                "name": "New",
                                "aliases": [],
                            }
                        ]
                        if any(event["event_id"] == "event:new" for event in events)
                        else []
                    ),
                ],
                "events": events,
                "relations": [],
                "unknowns": unknowns,
                "conflicts": [],
            },
            "verification_result": {
                "verification_version": "1.0",
                "ruleset_id": "ruleset.core.v1",
                "target_claim_id": "world:test",
                "status": verification_status,
                "reasons": reasons,
                "required_info": required_info,
                "receipts": {
                    "bundle_sha256": "bundle",
                    "output_sha256": output_sha256,
                    "attestation_sha256": attestation_sha256,
                    "ruleset_sha256": "ruleset",
                    "evidence_refs": [],
                    "proofs": [],
                    "findings": [],
                },
            },
        },
        "__meta__": {
            "output_sha256": output_sha256,
            "attestation_sha256": attestation_sha256,
        },
    }


def test_compute_world_diff_is_deterministic_and_matches_fixture():
    old_output = _wrapped_output(
        world_sha256="old-world",
        output_sha256="1111",
        attestation_sha256="aaaa",
        events=[
            {
                "event_id": "event:changed",
                "type": "Rotation",
                "time": {"kind": "date", "value": "2026-03-01"},
                "actors": [],
                "objects": [],
                "action": "rotated today",
                "state": None,
                "evidence": [],
            },
            {
                "event_id": "event:shared",
                "type": "Config",
                "time": {"kind": "unknown"},
                "actors": [],
                "objects": [],
                "action": "shared",
                "state": None,
                "evidence": [],
            },
        ],
        unknowns=[{"kind": "missing_time", "ref": {"event_id": "event:changed"}}],
        verification_status="VERIFIED_OK",
        reasons=[],
        required_info=[],
    )
    new_output = _wrapped_output(
        world_sha256="new-world",
        output_sha256="2222",
        attestation_sha256="bbbb",
        events=[
            {
                "event_id": "event:changed",
                "type": "Rotation",
                "time": {"kind": "date", "value": "2026-03-02"},
                "actors": [],
                "objects": [],
                "action": "rotated yesterday",
                "state": None,
                "evidence": [],
            },
            {
                "event_id": "event:shared",
                "type": "Config",
                "time": {"kind": "unknown"},
                "actors": [],
                "objects": [],
                "action": "shared",
                "state": None,
                "evidence": [],
            },
            {
                "event_id": "event:new",
                "type": "Access",
                "time": {"kind": "unknown"},
                "actors": [],
                "objects": [],
                "action": "new",
                "state": None,
                "evidence": [],
            },
        ],
        unknowns=[{"kind": "missing_actor", "ref": {"event_id": "event:new"}}],
        verification_status="VERIFIED_FAIL",
        reasons=[
            {
                "code": "RULE_CONTRADICTION",
                "message": "contradiction",
                "ref": {"event_id": "event:new"},
            }
        ],
        required_info=[{"kind": "missing_actor", "ref": {"event_id": "event:new"}}],
    )

    first = compute_world_diff(old_output=old_output, new_output=new_output)
    second = compute_world_diff(old_output=old_output, new_output=new_output)

    assert first == second
    expected = json.loads(
        (FIXTURES / "world_diff_expected.json").read_text(encoding="utf-8")
    )
    assert first == expected
