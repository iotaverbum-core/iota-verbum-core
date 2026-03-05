import json
from pathlib import Path

from core.reasoning.claim_graph import (
    claim_fingerprint,
    find_duplicates_and_contradictions,
    normalize_text,
)

FIXTURES = Path("tests/fixtures")


def test_find_duplicates_and_contradictions_matches_expected_fixture():
    graph = json.loads(
        (FIXTURES / "claim_graph_example.json").read_text(encoding="utf-8")
    )
    expected = json.loads(
        (FIXTURES / "graph_findings_expected.json").read_text(encoding="utf-8")
    )

    findings = find_duplicates_and_contradictions(graph)

    assert findings == expected


def test_claim_normalization_and_fingerprint_are_stable():
    graph = json.loads(
        (FIXTURES / "claim_graph_example.json").read_text(encoding="utf-8")
    )

    assert normalize_text("  Sky\tIS\nBlue  ") == "sky is blue"
    assert claim_fingerprint(graph["claims"][0]) == claim_fingerprint(
        graph["claims"][1]
    )
