import json
from pathlib import Path

from core.reasoning.critical_path import compute_critical_path

FIXTURES = Path("tests/fixtures")


def _fixture_causal_graph() -> dict:
    return json.loads(
        (FIXTURES / "causal_graph_expected.json").read_text(encoding="utf-8")
    )


def _cycle_causal_graph() -> dict:
    return {
        "version": "1.0",
        "nodes": [
            "event:" + ("1" * 64),
            "event:" + ("2" * 64),
        ],
        "edges": [
            {
                "from_event_id": "event:" + ("1" * 64),
                "to_event_id": "event:" + ("2" * 64),
                "type": "before",
                "reason_code": "RULE_TIME_PHRASE_BEFORE",
                "confidence": "medium",
                "evidence": [],
            },
            {
                "from_event_id": "event:" + ("2" * 64),
                "to_event_id": "event:" + ("1" * 64),
                "type": "before",
                "reason_code": "RULE_TIME_PHRASE_BEFORE",
                "confidence": "medium",
                "evidence": [],
            },
        ],
        "causal_order": [],
        "findings": [
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
        ],
    }


def _tied_chain_graph() -> dict:
    return {
        "version": "1.0",
        "nodes": [
            "event:" + ("1" * 64),
            "event:" + ("2" * 64),
            "event:" + ("3" * 64),
            "event:" + ("4" * 64),
        ],
        "edges": [
            {
                "from_event_id": "event:" + ("1" * 64),
                "to_event_id": "event:" + ("4" * 64),
                "type": "before",
                "reason_code": "RULE_TIME_EXPLICIT_DATE",
                "confidence": "high",
                "evidence": [],
            },
            {
                "from_event_id": "event:" + ("2" * 64),
                "to_event_id": "event:" + ("3" * 64),
                "type": "before",
                "reason_code": "RULE_TIME_EXPLICIT_DATE",
                "confidence": "high",
                "evidence": [],
            },
        ],
        "causal_order": [
            "event:" + ("1" * 64),
            "event:" + ("2" * 64),
            "event:" + ("3" * 64),
            "event:" + ("4" * 64),
        ],
        "findings": [],
    }


def test_compute_critical_path_is_stable_and_matches_fixture():
    causal_graph = _fixture_causal_graph()
    first = compute_critical_path(causal_graph)
    second = compute_critical_path(causal_graph)
    expected = json.loads(
        (FIXTURES / "critical_path_expected.json").read_text(encoding="utf-8")
    )

    assert first == second
    assert first == expected


def test_compute_critical_path_returns_empty_chain_when_before_cycle_exists():
    critical_path = compute_critical_path(_cycle_causal_graph())

    assert critical_path["critical_chain"] == []
    assert critical_path["receipts"]["cycle_detected"] is True


def test_compute_critical_path_uses_lexicographic_chain_tie_break():
    critical_path = compute_critical_path(_tied_chain_graph(), top_k=4)

    assert critical_path["critical_chain"] == [
        "event:" + ("1" * 64),
        "event:" + ("4" * 64),
    ]
    assert [item["event_id"] for item in critical_path["top_events"][:2]] == [
        "event:" + ("1" * 64),
        "event:" + ("2" * 64),
    ]
