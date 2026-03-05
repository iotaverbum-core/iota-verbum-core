from pathlib import Path

from tests.test_constraint_diff import _new_output, _old_output

from core.reasoning.constraint_diff import compute_constraint_diff
from core.reasoning.constraint_diff_narrative_v2 import (
    render_constraint_diff_narrative_v2,
)

FIXTURES = Path("tests/fixtures")


def test_render_constraint_diff_narrative_v2_matches_fixture():
    diff = compute_constraint_diff(old_output=_old_output(), new_output=_new_output())
    narrative = render_constraint_diff_narrative_v2(
        diff,
        mode="brief",
        max_lines=40,
    )
    expected = (FIXTURES / "constraint_diff_narrative_expected.txt").read_text(
        encoding="utf-8"
    )

    assert narrative["text"] == expected
    assert "\r" not in narrative["text"]
