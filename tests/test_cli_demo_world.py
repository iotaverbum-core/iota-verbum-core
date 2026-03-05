import json
from pathlib import Path

from proposal.cli_demo import main, run_demo


def test_run_demo_world_is_deterministic_across_runs(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Access Policy\n"
        "- 2026-03-01 `API_KEYS` are environment only.\n"
        "- 2026-03-02 `API_KEYS` are never in source.\n"
        "- Rotation policy is mandatory.\n",
        encoding="utf-8",
    )

    first = run_demo(
        folder=str(docs_dir),
        query="API_KEYS",
        prompt="Show me the world model",
        max_chunks=5,
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        world=True,
    )
    second = run_demo(
        folder=str(docs_dir),
        query="API_KEYS",
        prompt="Show me the world model",
        max_chunks=5,
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        world=True,
    )

    assert first["report"] == second["report"]
    assert first["run_dir"] == second["run_dir"]
    assert "__conflict_" not in first["run_dir"]
    for key in [
        "pack_path",
        "bundle_path",
        "world_model_path",
        "output_path",
        "attestation_path",
    ]:
        assert Path(first[key]).read_bytes() == Path(second[key]).read_bytes()
    assert "Deterministic World Demo\n" in first["report"]
    assert "world_sha256:" in first["report"]
    assert "World Narrative\n" in first["report"]
    assert "Causal Summary\n" in first["report"]
    assert "Critical Path\n" in first["report"]
    assert "Constraint Summary\n" in first["report"]
    assert "Repair Hints\n" in first["report"]
    assert "Causal Narrative\n" in first["report"]
    assert "Verification\n" in first["report"]
    output_obj = json.loads(Path(first["output_path"]).read_text(encoding="utf-8"))
    assert "causal_graph" in output_obj
    assert "causal_narrative_v2" in output_obj
    assert "critical_path" in output_obj
    assert "critical_path_narrative_v2" in output_obj
    assert "constraint_report" in output_obj
    assert "constraint_narrative_v2" in output_obj
    assert "repair_hints" in output_obj
    assert "repair_hints_narrative_v2" in output_obj
    assert "world_model" in output_obj
    assert "world_narrative" in output_obj
    assert "world_narrative_v2" in output_obj
    assert output_obj["world_model"]["world_sha256"] == first["world_sha256"]


def test_cli_demo_world_focus_keeps_event_count_bounded(
    tmp_path: Path,
    capsys,
):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    for index in range(35):
        (docs_dir / f"doc_{index}.md").write_text(
            "# Access Control\n"
            f"- access control event {index} keeps `API_KEYS` in environment only.\n",
            encoding="utf-8",
        )

    exit_code = main(
        [
            "--folder",
            str(docs_dir),
            "--query",
            "access control",
            "--prompt",
            "Show me the world model",
            "--max-chunks",
            "35",
            "--created-utc",
            "2026-03-01T12:00:00Z",
            "--core-version",
            "0.3.0",
            "--ruleset-id",
            "ruleset.core.v1",
            "--world",
            "true",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "WARNING: world.events=" not in captured.out


def test_run_demo_world_with_enrichment_reduces_unknowns_and_unlocks_causal_edge(
    tmp_path: Path,
):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Notes\n"
        "- 2026-03-01 keys are never in source\n"
        "- 2026-03-02 keys are environment only\n",
        encoding="utf-8",
    )

    base = run_demo(
        folder=str(docs_dir),
        query="keys",
        prompt="Show me the world model",
        max_chunks=5,
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        world=True,
    )
    base_output = json.loads(Path(base["output_path"]).read_text(encoding="utf-8"))
    base_unknown_count = len(base_output["world_model"]["unknowns"])
    base_edge_count = len(base_output["causal_graph"]["edges"])

    event_ids_by_action = {
        event["action"]: event["event_id"]
        for event in base_output["world_model"]["events"]
    }
    enrich_path = tmp_path / "enrichment.json"
    enrich_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "events": [
                    {
                        "event_id": event_ids_by_action[
                            "2026-03-01 keys are never in source"
                        ],
                        "actors": ["secops"],
                        "objects": ["API_KEYS"],
                    },
                    {
                        "event_id": event_ids_by_action[
                            "2026-03-02 keys are environment only"
                        ],
                        "actors": ["release"],
                        "objects": ["API_KEYS"],
                    },
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
        newline="\n",
    )

    enriched = run_demo(
        folder=str(docs_dir),
        query="keys",
        prompt="Show me the world model",
        max_chunks=5,
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        world=True,
        enrich=str(enrich_path),
    )
    enriched_output = json.loads(
        Path(enriched["output_path"]).read_text(encoding="utf-8")
    )

    assert "world_enrichment" in enriched_output
    assert len(enriched_output["world_model"]["unknowns"]) < base_unknown_count
    assert len(enriched_output["causal_graph"]["edges"]) > base_edge_count
    assert any(
        edge["type"] == "enables"
        for edge in enriched_output["causal_graph"]["edges"]
    )
