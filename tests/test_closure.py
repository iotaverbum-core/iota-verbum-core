import json
from pathlib import Path

from core.reasoning.closure import compute_closure

FIXTURES = Path("tests/fixtures")


def test_compute_closure_derives_shortest_paths_in_stable_order():
    graph = json.loads(
        (FIXTURES / "claim_graph_closure_example.json").read_text(encoding="utf-8")
    )

    derived = compute_closure(graph)

    assert derived["derived_version"] == "1.0"
    assert derived["derived_edges"] == [
        {
            "from_id": "D1",
            "to_id": "D3",
            "type": "depends_on",
            "proof": [
                {"from_id": "D1", "to_id": "D2", "type": "depends_on"},
                {"from_id": "D2", "to_id": "D3", "type": "depends_on"},
            ],
        },
        {
            "from_id": "I1",
            "to_id": "I3",
            "type": "implies",
            "proof": [
                {"from_id": "I1", "to_id": "I2", "type": "implies"},
                {"from_id": "I2", "to_id": "I3", "type": "implies"},
            ],
        },
        {
            "from_id": "A",
            "to_id": "C",
            "type": "supports",
            "proof": [
                {"from_id": "A", "to_id": "B", "type": "supports"},
                {"from_id": "B", "to_id": "C", "type": "supports"},
            ],
        },
    ]


def test_compute_closure_does_not_emit_duplicates():
    graph = json.loads(
        (FIXTURES / "claim_graph_closure_example.json").read_text(encoding="utf-8")
    )

    derived = compute_closure(graph)
    keys = [
        (edge["type"], edge["from_id"], edge["to_id"])
        for edge in derived["derived_edges"]
    ]

    assert len(keys) == len(set(keys))
    assert all(len(edge["proof"]) == 2 for edge in derived["derived_edges"])
