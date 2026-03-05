import json
from pathlib import Path

from core.determinism.finalize import finalize
from core.reasoning.cli_counterfactual import main
from core.reasoning.counterfactual import (
    canonicalize_counterfactual_task,
    compute_task_id,
)

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
            "prompt": "counterfactual fixture",
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
            "core_version": "0.3.0",
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
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:00:00Z",
    )
    (base_dir / "output.json").write_bytes(sealed["output_bytes"])
    (base_dir / "attestation.json").write_bytes(sealed["attestation_bytes"])
    (base_dir / "evidence_bundle.json").write_bytes(sealed["bundle_bytes"])
    return base_dir / "output.json"


def _normalize_result(result_obj: dict) -> dict:
    normalized = json.loads(json.dumps(result_obj))
    normalized["task_id"] = "FIXTURE_TASK_ID"
    normalized["receipts"]["base_path"] = "FIXTURE_BASE_OUTPUT_PATH"
    normalized["receipts"]["counterfactual_path"] = "FIXTURE_COUNTERFACTUAL_PATH"
    normalized["base_hashes"]["attestation_sha256"] = "FIXTURE_BASE_ATTESTATION_SHA256"
    normalized["counterfactual_hashes"]["attestation_sha256"] = (
        "FIXTURE_COUNTERFACTUAL_ATTESTATION_SHA256"
    )
    normalized["diff"]["old"]["attestation_sha256"] = "FIXTURE_BASE_ATTESTATION_SHA256"
    normalized["diff"]["new"]["attestation_sha256"] = (
        "FIXTURE_COUNTERFACTUAL_ATTESTATION_SHA256"
    )
    return normalized


def test_cli_counterfactual_writes_expected_files(tmp_path: Path, capsys):
    base_output_path = _write_base_source(tmp_path)
    task = {
        "version": "1.0",
        "task_id": "",
        "created_utc": "2026-03-05T00:00:00Z",
        "base": {
            "source": {
                "kind": "output_json",
                "path": str(base_output_path.as_posix()),
            }
        },
        "operation": {
            "type": "REMOVE_EVENT",
            "target_id": "event:" + ("3" * 64),
        },
        "options": {
            "mode": "brief",
            "max_lines": 80,
        },
    }
    task["task_id"] = compute_task_id(task)
    task_path = tmp_path / "task.json"
    task_path.write_bytes(canonicalize_counterfactual_task(task))

    exit_code = main(
        [
            "--task",
            str(task_path),
            "--out-dir",
            str((tmp_path / "out").as_posix()),
        ]
    )
    captured = capsys.readouterr()

    run_dir = tmp_path / "out" / task["task_id"].replace(":", "_")
    assert exit_code == 0
    assert f"task_id={task['task_id']}" in captured.out
    for name in [
        "task.json",
        "output.json",
        "attestation.json",
        "counterfactual_result.json",
        "counterfactual_narrative_v2.json",
        "counterfactual_narrative_v2.txt",
        "world_diff.json",
        "world_diff_narrative.json",
    ]:
        assert (run_dir / name).exists()

    result_obj = json.loads(
        (run_dir / "counterfactual_result.json").read_text(encoding="utf-8")
    )
    normalized = _normalize_result(result_obj)
    assert normalized["effects"]["removed"]["events"] == [
        "event:" + ("3" * 64)
    ]


def test_cli_counterfactual_can_fix_missing_task_id_and_then_run(
    tmp_path: Path,
    capsys,
):
    base_output_path = _write_base_source(tmp_path)
    task = {
        "version": "1.0",
        "created_utc": "2026-03-05T00:00:00Z",
        "base": {
            "source": {
                "kind": "output_json",
                "path": str(base_output_path.as_posix()),
            }
        },
        "operation": {
            "type": "REMOVE_EVENT",
            "target_id": "event:" + ("3" * 64),
        },
        "options": {
            "mode": "brief",
            "max_lines": 80,
        },
    }
    expected_task_id = compute_task_id(task)
    task_path = tmp_path / "task_missing_id.json"
    task_path.write_text(
        json.dumps(task, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    try:
        main(
            [
                "--task",
                str(task_path),
                "--out-dir",
                str((tmp_path / "out").as_posix()),
            ]
        )
    except SystemExit as exc:
        assert exc.code == 2
    captured = capsys.readouterr()
    assert f"expected task_id={expected_task_id}" in captured.err

    exit_code = main(
        [
            "--task",
            str(task_path),
            "--out-dir",
            str((tmp_path / "out").as_posix()),
            "--fix-task",
            "true",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == f"Wrote canonical task_id: {expected_task_id}"

    exit_code = main(
        [
            "--task",
            str(task_path),
            "--out-dir",
            str((tmp_path / "out").as_posix()),
            "--mode",
            "full",
        ]
    )
    captured = capsys.readouterr()
    run_dir = tmp_path / "out" / expected_task_id.replace(":", "_")
    narrative_obj = json.loads(
        (run_dir / "counterfactual_narrative_v2.json").read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert f"task_id={expected_task_id}" in captured.out
    assert narrative_obj["mode"] == "full"
    assert (run_dir / "counterfactual_narrative_v2.txt").exists()
