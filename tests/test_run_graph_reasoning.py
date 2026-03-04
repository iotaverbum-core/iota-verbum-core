import json
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.replay import verify_run
from core.reasoning.run_graph import run_graph_reasoning

FIXTURES = Path("tests/fixtures")


def _bundle() -> dict:
    return json.loads(
        (FIXTURES / "evidence_bundle_example.json").read_text(encoding="utf-8")
    )


def _graph() -> dict:
    return json.loads(
        (FIXTURES / "claim_graph_closure_example.json").read_text(encoding="utf-8")
    )


def test_run_graph_reasoning_seals_and_replays(tmp_path: Path):
    result = run_graph_reasoning(
        _bundle(),
        _graph(),
        manifest_sha256="1" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
        ledger_root=str(tmp_path),
        target_claim_id="C",
    )

    replay = verify_run(result["ledger_dir"], strict_manifest=False)

    assert replay["ok"] is True
    assert replay["bundle_sha256"] == result["bundle_sha256"]
    assert replay["output_sha256"] == result["output_sha256"]
    output = json.loads(result["output_bytes"].decode("utf-8"))

    assert "derived" in output
    assert "narrative" in output
    assert output["derived"]["derived_edges"] == [
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
    assert output["support_tree"] == {
        "support_tree_version": "1.0",
        "target_claim_id": "C",
        "nodes": [
            {
                "claim_id": "A",
                "claim": output["claim_graph"]["claims"][0],
            },
            {
                "claim_id": "B",
                "claim": output["claim_graph"]["claims"][1],
            },
            {
                "claim_id": "C",
                "claim": output["claim_graph"]["claims"][2],
            },
        ],
        "edges": [
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
        ],
    }
    assert output["narrative"]["target_claim_id"] == "C"
    assert result["output_bytes"] == dumps_canonical(output)
