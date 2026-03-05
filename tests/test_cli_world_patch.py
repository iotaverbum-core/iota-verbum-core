import json
from pathlib import Path

from core.determinism.finalize import finalize
from core.reasoning.cli_world_patch import main

FIXTURES = Path("tests/fixtures")
_TEXTS = {
    "chunk:1": "Policy says API_KEYS are never in source.",
    "chunk:2": "Config keeps API_KEYS environment only.",
    "chunk:3": "API_KEYS access review pending actor and time.",
}
_OFFSETS = {
    "chunk:1": (0, 39),
    "chunk:2": (40, 79),
    "chunk:3": (80, 119),
}


def _base_output() -> dict:
    return json.loads(
        (FIXTURES / "counterfactual_base_output.json").read_text(encoding="utf-8")
    )


def _write_base_source(tmp_path: Path) -> Path:
    evidence = {}
    for event in _base_output()["world_model"]["events"]:
        for ref in event["evidence"]:
            evidence[ref["chunk_id"]] = ref["text_sha256"]
    bundle = {
        "bundle_version": "1.0",
        "created_utc": "2026-03-01T12:00:00Z",
        "inputs": {
            "prompt": "world patch fixture",
            "params": {},
        },
        "artifacts": [
            {
                "source_id": "doc:1",
                "chunk_id": chunk_id,
                "offset_start": _OFFSETS[chunk_id][0],
                "offset_end": _OFFSETS[chunk_id][1],
                "text": _TEXTS[chunk_id],
                "text_sha256": evidence[chunk_id],
            }
            for chunk_id in sorted(evidence)
        ],
        "toolchain": {
            "core_version": "0.4.0",
            "parser_versions": {},
            "schema_versions": {
                "attestation_record": "1.0",
                "evidence_bundle": "1.0",
                "evidence_pack": "1.0",
            },
        },
        "policy": {
            "ruleset_id": "ruleset.core.v1",
        },
    }
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    sealed = finalize(
        bundle,
        _base_output(),
        manifest_sha256="1" * 64,
        core_version="0.4.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:00:00Z",
    )
    (base_dir / "output.json").write_bytes(sealed["output_bytes"])
    (base_dir / "attestation.json").write_bytes(sealed["attestation_bytes"])
    (base_dir / "evidence_bundle.json").write_bytes(sealed["bundle_bytes"])
    return base_dir / "output.json"


def _normalize_result(result_obj: dict) -> dict:
    normalized = json.loads(json.dumps(result_obj))
    normalized["patch_id"] = "FIXTURE_PATCH_ID"
    normalized["new"]["world_sha256"] = "FIXTURE_NEW_WORLD_SHA256"
    normalized["new"]["output_sha256"] = "FIXTURE_NEW_OUTPUT_SHA256"
    normalized["new"]["attestation_sha256"] = "FIXTURE_NEW_ATTESTATION_SHA256"
    normalized["base"]["output_sha256"] = "FIXTURE_BASE_OUTPUT_SHA256"
    normalized["base"]["attestation_sha256"] = "FIXTURE_BASE_ATTESTATION_SHA256"
    normalized["ledger_dir"] = "FIXTURE_LEDGER_DIR"
    normalized["receipts"]["patch_sha256"] = "FIXTURE_PATCH_SHA256"
    normalized.pop("world_diff", None)
    normalized.pop("constraint_diff", None)
    return normalized


def _normalize_narrative(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("Patch: patch:", "Patch: FIXTURE_PATCH_ID")
    text = text.replace(
        "New world_sha256: ", "New world_sha256: FIXTURE_NEW_WORLD_SHA256"
    )
    text = text.replace("patch_sha256: ", "patch_sha256: FIXTURE_PATCH_SHA256")
    text = text.replace("ledger_dir: ", "ledger_dir: FIXTURE_LEDGER_DIR")
    return text


def test_cli_world_patch_end_to_end(tmp_path: Path, capsys):
    base_output_path = _write_base_source(tmp_path)
    patch = json.loads(
        (FIXTURES / "world_patch_example.json").read_text(encoding="utf-8")
    )
    patch["base_ref"]["value"] = str(base_output_path.as_posix())
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(json.dumps(patch, indent=2), encoding="utf-8", newline="\n")

    exit_code = main(
        [
            "--base",
            str(base_output_path),
            "--patch",
            str(patch_path),
            "--out-dir",
            str((tmp_path / "out").as_posix()),
            "--created-utc",
            "2026-03-05T00:00:00Z",
            "--core-version",
            "0.4.0",
            "--ruleset-id",
            "ruleset.core.v1",
            "--with-diff",
            "true",
            "--with-constraint-diff",
            "true",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "patch_id=patch:" in captured.out

    out_root = tmp_path / "out"
    run_dirs = [item for item in out_root.iterdir() if item.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    for name in [
        "patch.json",
        "output.json",
        "attestation.json",
        "world_patch_result.json",
        "world_patch_narrative_v2.json",
        "world_patch_narrative_v2.txt",
        "world_diff.json",
        "constraint_diff.json",
    ]:
        assert (run_dir / name).exists()

    result_obj = json.loads(
        (run_dir / "world_patch_result.json").read_text(encoding="utf-8")
    )
    expected_result = json.loads(
        (FIXTURES / "world_patch_result_expected.json").read_text(encoding="utf-8")
    )
    assert _normalize_result(result_obj) == expected_result

    expected_narrative = (FIXTURES / "world_patch_narrative_expected.txt").read_text(
        encoding="utf-8"
    )
    actual_narrative = _normalize_narrative(
        (run_dir / "world_patch_narrative_v2.txt").read_text(encoding="utf-8")
    )
    assert "VERIFIED_NEEDS_INFO -> VERIFIED_OK" in actual_narrative
    assert actual_narrative.startswith("Summary\n")
    assert "\r" not in actual_narrative
    assert expected_narrative.splitlines()[0] == actual_narrative.splitlines()[0]
