import json
from pathlib import Path

from core.reasoning.repair_hints import compute_repair_hints

FIXTURES = Path("tests/fixtures")


def _fixture() -> dict:
    return json.loads(
        (FIXTURES / "repair_hints_world_example.json").read_text(encoding="utf-8")
    )


def test_compute_repair_hints_is_stable_and_matches_fixture():
    fixture = _fixture()
    first = compute_repair_hints(
        fixture["constraint_report"],
        fixture["causal_graph"],
        fixture["world_model"],
    )
    second = compute_repair_hints(
        fixture["constraint_report"],
        fixture["causal_graph"],
        fixture["world_model"],
    )
    expected = json.loads(
        (FIXTURES / "repair_hints_expected.json").read_text(encoding="utf-8")
    )

    assert first == second
    assert first == expected


def test_compute_repair_hints_orders_by_rule_and_hint_id():
    fixture = _fixture()
    repair_hints = compute_repair_hints(
        fixture["constraint_report"],
        fixture["causal_graph"],
        fixture["world_model"],
    )

    assert [hint["violation_type"] for hint in repair_hints["hints"]] == [
        "CAUSAL_CONFLICT",
        "CAUSAL_CONFLICT",
        "POLICY_CONFLICT",
        "POLICY_CONFLICT",
        "STATE_CONFLICT",
        "STATE_CONFLICT",
        "TEMPORAL_CONFLICT",
        "TEMPORAL_CONFLICT",
    ]
    assert all(hint["hint_id"].startswith("hint:") for hint in repair_hints["hints"])
    assert repair_hints["hints"][0]["action"] == "DROP_EDGE"
    assert repair_hints["hints"][-1]["action"] == "MARK_TIME_UNKNOWN"
