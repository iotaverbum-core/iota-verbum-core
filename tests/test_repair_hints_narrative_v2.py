import json
from pathlib import Path

from core.reasoning.repair_hints import compute_repair_hints
from core.reasoning.repair_hints_narrative_v2 import (
    render_repair_hints_narrative_v2,
)

FIXTURES = Path("tests/fixtures")


def test_render_repair_hints_narrative_v2_matches_golden_text():
    fixture = json.loads(
        (FIXTURES / "repair_hints_world_example.json").read_text(encoding="utf-8")
    )
    repair_hints = compute_repair_hints(
        fixture["constraint_report"],
        fixture["causal_graph"],
        fixture["world_model"],
    )
    narrative = render_repair_hints_narrative_v2(
        repair_hints,
        max_lines=40,
        verbosity="brief",
    )
    expected = (FIXTURES / "repair_hints_narrative_expected.txt").read_text(
        encoding="utf-8"
    )

    assert narrative["text"] == expected
    assert "\r" not in narrative["text"]
