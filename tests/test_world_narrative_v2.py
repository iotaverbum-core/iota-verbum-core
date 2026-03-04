import json
from pathlib import Path

from core.reasoning.world_narrative_v2 import render_world_narrative_v2

FIXTURES = Path("tests/fixtures")


def _world_model() -> dict:
    return {
        "world_version": "1.0",
        "world_sha256": "d" * 64,
        "entities": [
            {
                "entity_id": "entity:" + ("a" * 64),
                "type": "Secret",
                "name": "API_KEYS",
                "aliases": [],
            }
        ],
        "events": [
            {
                "event_id": "event:" + ("a" * 64),
                "type": "Config",
                "time": {"kind": "date", "value": "2026-03-01"},
                "actors": [],
                "objects": ["entity:" + ("a" * 64)],
                "action": "API keys configured for env-only use",
                "state": {"API_KEYS": "env-only"},
                "evidence": [
                    {
                        "source_id": "doc:1",
                        "chunk_id": "chunk:1",
                        "offset_start": 0,
                        "offset_end": 10,
                        "text_sha256": "1" * 64,
                    }
                ],
            },
            {
                "event_id": "event:" + ("b" * 64),
                "type": "Rotation",
                "time": {"kind": "unknown"},
                "actors": [],
                "objects": [],
                "action": "Rotation scheduled without a date",
                "state": None,
                "evidence": [
                    {
                        "source_id": "doc:2",
                        "chunk_id": "chunk:2",
                        "offset_start": 11,
                        "offset_end": 20,
                        "text_sha256": "2" * 64,
                    }
                ],
            },
        ],
        "relations": [],
        "unknowns": [
            {"kind": "missing_time", "ref": {"event_id": "event:" + ("b" * 64)}}
        ],
        "conflicts": [
            {
                "kind": "state_conflict",
                "ref": {
                    "entity_id": "entity:" + ("a" * 64),
                    "event_ids": [
                        "event:" + ("a" * 64),
                        "event:" + ("c" * 64),
                    ],
                    "key": "API_KEYS",
                    "values": ["env-only", "never-in-repo"],
                },
                "reason": "API_KEYS has conflicting states: env-only, never-in-repo",
            }
        ],
    }


def _verification_result() -> dict:
    return {
        "verification_version": "1.0",
        "ruleset_id": "ruleset.core.v1",
        "target_claim_id": "world:test",
        "status": "VERIFIED_NEEDS_INFO",
        "reasons": [
            {
                "code": "RULE_WORLD_UNKNOWNS_SECURITY",
                "message": "security-relevant world event is missing required context",
                "ref": {"event_id": "event:" + ("b" * 64)},
            }
        ],
        "required_info": [
            {"kind": "missing_time", "ref": {"event_id": "event:" + ("b" * 64)}}
        ],
        "receipts": {
            "bundle_sha256": "a" * 64,
            "output_sha256": "b" * 64,
            "attestation_sha256": "",
            "ruleset_sha256": "c" * 64,
            "evidence_refs": [
                {
                    "source_id": "doc:1",
                    "chunk_id": "chunk:1",
                    "offset_start": 0,
                    "offset_end": 10,
                    "text_sha256": "1" * 64,
                },
                {
                    "source_id": "doc:2",
                    "chunk_id": "chunk:2",
                    "offset_start": 11,
                    "offset_end": 20,
                    "text_sha256": "2" * 64,
                },
            ],
            "proofs": [],
            "findings": [],
        },
    }


def test_render_world_narrative_v2_brief_is_stable_and_bounded():
    first = render_world_narrative_v2(
        world_model=_world_model(),
        verification_result=_verification_result(),
        mode="brief",
        show_receipts=False,
        max_lines=40,
    )
    second = render_world_narrative_v2(
        world_model=_world_model(),
        verification_result=_verification_result(),
        mode="brief",
        show_receipts=False,
        max_lines=40,
    )

    assert first == second
    assert len(first["text"].splitlines()) <= 40
    expected = (FIXTURES / "world_narrative_v2_expected.txt").read_text(
        encoding="utf-8"
    )
    assert first["text"] == expected


def test_render_world_narrative_v2_full_with_receipts_expands_deterministically():
    brief = render_world_narrative_v2(
        world_model=_world_model(),
        verification_result=_verification_result(),
        mode="brief",
        show_receipts=False,
        max_lines=40,
    )
    full = render_world_narrative_v2(
        world_model=_world_model(),
        verification_result=_verification_result(),
        mode="full",
        show_receipts=True,
        max_lines=80,
    )

    assert full["text"] != brief["text"]
    assert "evidence: " in full["text"]
    assert json.loads(json.dumps(full)) == full
