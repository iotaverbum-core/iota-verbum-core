import json
from pathlib import Path

from core.reasoning.causal import compute_causal_graph
from core.reasoning.causal_narrative_v2 import render_causal_narrative_v2

FIXTURES = Path("tests/fixtures")


def test_render_causal_narrative_v2_matches_golden_text():
    world_model = json.loads(
        (FIXTURES / "causal_world_example.json").read_text(encoding="utf-8")
    )
    causal_graph = compute_causal_graph(world_model)

    narrative = render_causal_narrative_v2(
        causal_graph,
        max_lines=40,
        verbosity="brief",
    )
    expected = (FIXTURES / "causal_narrative_v2_expected.txt").read_text(
        encoding="utf-8"
    )

    assert narrative["text"] == expected
    assert "\r" not in narrative["text"]
