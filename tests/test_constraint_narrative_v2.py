import json
from pathlib import Path

from core.reasoning.constraint_narrative_v2 import render_constraint_narrative_v2
from core.reasoning.constraints import compute_constraints

FIXTURES = Path("tests/fixtures")


def test_render_constraint_narrative_v2_matches_golden_text():
    fixture = json.loads(
        (FIXTURES / "constraint_world_example.json").read_text(encoding="utf-8")
    )
    constraint_report = compute_constraints(
        fixture["world_model"],
        fixture["causal_graph"],
    )
    narrative = render_constraint_narrative_v2(
        constraint_report,
        mode="brief",
        max_lines=40,
    )
    expected = (FIXTURES / "constraint_narrative_expected.txt").read_text(
        encoding="utf-8"
    )

    assert narrative["text"] == expected
    assert "\r" not in narrative["text"]
