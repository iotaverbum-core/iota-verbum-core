import json
from pathlib import Path

from core.reasoning.causal import compute_causal_graph

FIXTURES = Path("tests/fixtures")


def _fixture_world() -> dict:
    return json.loads(
        (FIXTURES / "causal_world_example.json").read_text(encoding="utf-8")
    )


def _cycle_world() -> dict:
    object_id = "entity:" + ("a" * 64)
    return {
        "world_version": "1.0",
        "world_sha256": "f" * 64,
        "entities": [
            {
                "entity_id": object_id,
                "type": "Secret",
                "name": "API_KEYS",
                "aliases": [],
            }
        ],
        "events": [
            {
                "event_id": "event:" + ("1" * 64),
                "type": "Rotation",
                "time": {"kind": "date", "value": "2026-03-04"},
                "actors": ["secops"],
                "objects": [object_id],
                "action": "API_KEYS rotated after deployment.",
                "state": None,
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
                "event_id": "event:" + ("2" * 64),
                "type": "Deployment",
                "time": {"kind": "date", "value": "2026-03-04"},
                "actors": ["release"],
                "objects": [object_id],
                "action": "API_KEYS deployment after rotation.",
                "state": None,
                "evidence": [
                    {
                        "source_id": "doc:1",
                        "chunk_id": "chunk:2",
                        "offset_start": 11,
                        "offset_end": 20,
                        "text_sha256": "2" * 64,
                    }
                ],
            },
        ],
        "relations": [],
        "unknowns": [],
        "conflicts": [],
    }


def test_compute_causal_graph_is_stable_across_runs():
    world_model = _fixture_world()

    first = compute_causal_graph(world_model)
    second = compute_causal_graph(world_model)
    expected = json.loads(
        (FIXTURES / "causal_graph_expected.json").read_text(encoding="utf-8")
    )

    assert first == second
    assert first == expected


def test_compute_causal_graph_canonicalizes_after_to_before():
    causal_graph = compute_causal_graph(_fixture_world())

    assert all(edge["type"] != "after" for edge in causal_graph["edges"])
    assert {
        "from_event_id": "event:" + ("3" * 64),
        "to_event_id": "event:" + ("4" * 64),
        "type": "before",
    }.items() <= next(
        edge.items()
        for edge in causal_graph["edges"]
        if edge["reason_code"] == "RULE_TIME_PHRASE_BEFORE"
    )


def test_compute_causal_graph_detects_temporal_cycle_deterministically():
    first = compute_causal_graph(_cycle_world())
    second = compute_causal_graph(_cycle_world())

    assert first == second
    assert first["causal_order"] == []
    assert first["findings"] == [
        {
            "code": "CYCLE_TEMPORAL_CONSTRAINT",
            "message": "Temporal before edges contain a cycle",
            "event_ids": sorted(
                [
                    "event:" + ("1" * 64),
                    "event:" + ("2" * 64),
                ]
            ),
            "details": {"edge_count": 2},
        }
    ]


def test_compute_causal_graph_uses_stable_topological_tie_break():
    causal_graph = compute_causal_graph(_fixture_world())

    assert causal_graph["causal_order"] == [
        "event:" + ("1" * 64),
        "event:" + ("2" * 64),
        "event:" + ("6" * 64),
        "event:" + ("3" * 64),
        "event:" + ("4" * 64),
        "event:" + ("5" * 64),
    ]
