from __future__ import annotations

import json
from pathlib import Path

import core.path_compiler as path_compiler_module
from core.pipeline import DeterministicPipeline
from core.world.forward_projection import ForwardProjection
from domains.market_realtime.extractors import build_sample_dji_input
from domains.market_realtime.integration import (
    MarketRealtimePipelineAdapter,
    compile_market_forward_artifacts,
)


def _run_market_pipeline(output_dir: Path) -> dict:
    adapter = MarketRealtimePipelineAdapter()
    adapter.set_input_ref("DJI-2026-03-19")
    pipeline = DeterministicPipeline(
        "market_realtime",
        adapter,
        Path("src/domains/market_realtime/templates"),
        manifest_path=Path("data/market/manifest.json"),
    )
    input_data = build_sample_dji_input()
    input_bytes = json.dumps(input_data, sort_keys=True).encode("utf-8")
    result = pipeline.process(
        "DJI-2026-03-19",
        input_data,
        input_bytes,
        {"mode": "forward", "horizon": "86400"},
        output_dir,
    )
    result["forward_projection"] = compile_market_forward_artifacts(
        output_dir,
        result["output_data"],
        {"mode": "forward", "horizon": "86400"},
    )
    return result


def test_market_forward_projection_writes_replay_artifacts(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(path_compiler_module, "_repo_root", lambda: tmp_path)
    output_dir = tmp_path / "outputs" / "market" / "dji_20260319"

    result = _run_market_pipeline(output_dir)
    replay = ForwardProjection.verify_replay(output_dir / "sealed_path.json")
    casefile = json.loads((output_dir / "casefile.json").read_text(encoding="utf-8"))

    assert replay["match"] is True
    assert replay["status"] == "VERIFIED_OK"
    assert result["forward_projection"]["verified"] is True
    assert (output_dir / "forward_attestation.sha256").exists()
    assert (output_dir / "replay_manifest.json").exists()
    assert any(
        artifact["name"] == "sealed_path.json" and artifact["role"] == "sealed"
        for artifact in casefile["artifacts"]
    )


def test_market_forward_projection_seal_sha256_is_deterministic(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(path_compiler_module, "_repo_root", lambda: tmp_path)
    first_output_dir = tmp_path / "outputs" / "market" / "run1"
    second_output_dir = tmp_path / "outputs" / "market" / "run2"

    first = _run_market_pipeline(first_output_dir)
    second = _run_market_pipeline(second_output_dir)
    first_sealed = json.loads(
        (first_output_dir / "sealed_path.json").read_text(encoding="utf-8")
    )
    second_sealed = json.loads(
        (second_output_dir / "sealed_path.json").read_text(encoding="utf-8")
    )

    assert first["forward_projection"]["seal_sha256"] == second[
        "forward_projection"
    ]["seal_sha256"]
    assert first_sealed["seal_sha256"] == second_sealed["seal_sha256"]
