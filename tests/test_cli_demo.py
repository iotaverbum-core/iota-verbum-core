import json
from pathlib import Path

from proposal.cli_demo import run_demo


def test_run_demo_is_deterministic_across_runs(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Access Control\n- API keys stay in environment variables.\n"
        "- Secrets never belong in source control.\n"
        "- Rotation policy is mandatory.\n",
        encoding="utf-8",
    )

    first = run_demo(
        folder=str(docs_dir),
        query="rotation",
        prompt="Explain access control",
        max_chunks=5,
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
    )
    second = run_demo(
        folder=str(docs_dir),
        query="rotation",
        prompt="Explain access control",
        max_chunks=5,
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
    )

    assert first["report"] == second["report"]
    for key in [
        "pack_path",
        "claim_graph_path",
        "bundle_path",
        "output_path",
        "attestation_path",
    ]:
        assert Path(first[key]).read_bytes() == Path(second[key]).read_bytes()
    assert "Deterministic Demo\n" in first["report"]
    assert "pack_sha256:" in first["report"]
    assert "bundle_sha256:" in first["report"]
    assert "output_sha256:" in first["report"]
    assert "attestation_sha256:" in first["report"]
    assert "target_claim_id:" in first["report"]
    assert "Ledger Dir\n" in first["report"]
    assert "Replay Command\n" in first["report"]
    assert "target_claim:      Access Control | Rotation policy is mandatory." in (
        first["report"]
    )
    assert "Verification\n" in first["report"]
    assert "What we know\n" in first["report"]
    output_obj = json.loads(Path(first["output_path"]).read_text(encoding="utf-8"))
    assert "narrative" in output_obj
    assert "narrative_v2" in output_obj
    assert output_obj["narrative_v2"]["mode"] == "brief"
