import json
from pathlib import Path

import pytest

from core.reasoning.closure import compute_closure
from core.reasoning.support_tree import build_support_tree

FIXTURES = Path("tests/fixtures")


def _graph() -> dict:
    return json.loads(
        (FIXTURES / "claim_graph_closure_example.json").read_text(encoding="utf-8")
    )


def test_build_support_tree_includes_upstream_nodes_and_derived_edge():
    graph = _graph()
    derived = compute_closure(graph)

    support_tree = build_support_tree(graph, derived, "C")

    assert [node["claim_id"] for node in support_tree["nodes"]] == ["A", "B", "C"]
    assert support_tree["edges"] == [
        {
            "from_id": "A",
            "to_id": "B",
            "type": "supports",
            "derived": False,
            "proof": None,
        },
        {
            "from_id": "A",
            "to_id": "C",
            "type": "supports",
            "derived": True,
            "proof": [
                {"from_id": "A", "to_id": "B", "type": "supports"},
                {"from_id": "B", "to_id": "C", "type": "supports"},
            ],
        },
        {
            "from_id": "B",
            "to_id": "C",
            "type": "supports",
            "derived": False,
            "proof": None,
        },
    ]


def test_build_support_tree_raises_when_target_missing():
    graph = _graph()
    derived = compute_closure(graph)

    with pytest.raises(ValueError, match="target claim_id not found"):
        build_support_tree(graph, derived, "missing")
