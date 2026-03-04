import json
from pathlib import Path

from proposal.cli_demo import main, run_demo


def test_cli_demo_world_diff_writes_stable_artifacts_and_prints_header(
    tmp_path: Path,
    capsys,
):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Access Policy\n"
        "- 2026-03-01 `API_KEYS` are environment only.\n"
        "- 2026-03-02 `API_KEYS` are never in source.\n",
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

    exit_code = main(
        [
            "--folder",
            str(docs_dir),
            "--query",
            "API_KEYS",
            "--prompt",
            "Show me the world model",
            "--max-chunks",
            "5",
            "--created-utc",
            "2026-03-01T12:00:00Z",
            "--core-version",
            "0.3.0",
            "--ruleset-id",
            "ruleset.core.v1",
            "--world",
            "true",
            "--diff-against",
            first["ledger_dir"],
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "World Diff\n" in captured.out

    second = run_demo(
        folder=str(docs_dir),
        query="API_KEYS",
        prompt="Show me the world model",
        max_chunks=5,
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        world=True,
        diff_against=first["ledger_dir"],
    )

    assert Path(second["world_diff_path"]).exists()
    assert Path(second["world_diff_narrative_path"]).exists()
    assert Path(second["world_diff_path"]).read_bytes() == json.dumps(
        json.loads(Path(second["world_diff_path"]).read_text(encoding="utf-8")),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    rerun = run_demo(
        folder=str(docs_dir),
        query="API_KEYS",
        prompt="Show me the world model",
        max_chunks=5,
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        world=True,
        diff_against=first["ledger_dir"],
    )
    assert Path(second["world_diff_path"]).read_bytes() == Path(
        rerun["world_diff_path"]
    ).read_bytes()
    assert Path(second["world_diff_narrative_path"]).read_bytes() == Path(
        rerun["world_diff_narrative_path"]
    ).read_bytes()
