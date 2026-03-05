import json
from pathlib import Path

from proposal.cli_demo import run_demo


def test_run_demo_world_writes_casefile_and_is_stable(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Access Policy\n"
        "- 2026-03-01 API keys remain in environment variables.\n"
        "- 2026-03-02 API keys must never be committed.\n",
        encoding="utf-8",
    )

    first = run_demo(
        folder=str(docs_dir),
        query="API keys",
        prompt="build world",
        max_chunks=5,
        created_utc="2026-03-05T00:00:00Z",
        core_version="0.4.0",
        ruleset_id="ruleset.core.v1",
        world=True,
    )
    second = run_demo(
        folder=str(docs_dir),
        query="API keys",
        prompt="build world",
        max_chunks=5,
        created_utc="2026-03-05T00:00:00Z",
        core_version="0.4.0",
        ruleset_id="ruleset.core.v1",
        world=True,
    )

    assert first["casefile"]["casefile_id"] == second["casefile"]["casefile_id"]
    assert (
        Path(first["casefile_path"]).read_bytes()
        == Path(second["casefile_path"]).read_bytes()
    )
    assert "casefile_id:" in first["report"]
    assert "casefile_sha256:" in first["report"]

    sealed_output = json.loads(Path(first["output_path"]).read_text(encoding="utf-8"))
    assert "casefile" in sealed_output
    assert sealed_output["casefile"]["hashes"]["output_sha256"] == "0" * 64
    assert sealed_output["casefile"]["hashes"]["attestation_sha256"] == "0" * 64
