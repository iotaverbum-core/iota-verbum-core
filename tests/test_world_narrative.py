import json
from pathlib import Path

from core.reasoning.world_narrative import render_world_narrative

FIXTURES = Path("tests/fixtures")


def test_render_world_narrative_is_stable_and_has_receipts():
    world_model = {
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
            {
                "kind": "missing_time",
                "ref": {"event_id": "event:" + ("b" * 64)},
            }
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

    narrative = render_world_narrative(world_model)

    assert narrative["narrative_version"] == "1.0"
    assert [paragraph["pid"] for paragraph in narrative["paragraphs"]] == [
        "01-summary",
        "02-timeline",
        "03-unknowns",
        "04-conflicts",
    ]
    assert narrative["paragraphs"][1]["receipts"] == [
        {
            "kind": "evidence",
            "ref": {
                "source_id": "doc:1",
                "chunk_id": "chunk:1",
                "offset_start": 0,
                "offset_end": 10,
                "text_sha256": "1" * 64,
            },
        },
        {
            "kind": "evidence",
            "ref": {
                "source_id": "doc:2",
                "chunk_id": "chunk:2",
                "offset_start": 11,
                "offset_end": 20,
                "text_sha256": "2" * 64,
            },
        },
    ]
    assert narrative["paragraphs"][3]["receipts"] == [
        {
            "kind": "conflict",
            "ref": world_model["conflicts"][0],
        }
    ]
    timeline_lines = narrative["paragraphs"][1]["body"].splitlines()
    timeline_event_ids = [
        line.rsplit("event_id=", 1)[1].rstrip(")")
        for line in timeline_lines
        if "event_id=" in line
    ]
    assert len(timeline_event_ids) == len(set(timeline_event_ids))
    expected_text = (FIXTURES / "world_narrative_expected.txt").read_text(
        encoding="utf-8"
    )
    assert narrative["text"] == expected_text
    assert json.loads(json.dumps(narrative)) == narrative
