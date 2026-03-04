import json
from pathlib import Path

from core.reasoning.critical_path_narrative_v2 import (
    render_critical_path_narrative_v2,
)

FIXTURES = Path("tests/fixtures")


def test_render_critical_path_narrative_v2_matches_fixture():
    critical_path = json.loads(
        (FIXTURES / "critical_path_expected.json").read_text(encoding="utf-8")
    )
    narrative = render_critical_path_narrative_v2(
        critical_path,
        mode="brief",
        max_lines=40,
    )
    expected = (FIXTURES / "critical_path_narrative_expected.txt").read_text(
        encoding="utf-8"
    )

    assert narrative["text"] == expected
    assert "\r" not in narrative["text"]
