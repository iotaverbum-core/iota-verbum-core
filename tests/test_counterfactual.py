import json
from pathlib import Path

from core.determinism.finalize import finalize
from core.reasoning.counterfactual import (
    compute_counterfactual_task_id,
    compute_task_id,
    run_counterfactual_task,
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


def _task_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _artifact(chunk_id: str, text_sha256: str) -> dict:
    offset_start, offset_end = _OFFSETS[chunk_id]
    return {
        "source_id": "doc:1",
        "chunk_id": chunk_id,
        "offset_start": offset_start,
        "offset_end": offset_end,
        "text": _TEXTS[chunk_id],
        "text_sha256": text_sha256,
    }


def _bundle() -> dict:
    evidence = {}
    for event in _base_output()["world_model"]["events"]:
        for ref in event["evidence"]:
            evidence[ref["chunk_id"]] = ref["text_sha256"]
    return {
        "bundle_version": "1.0",
        "created_utc": "2026-03-01T12:00:00Z",
        "inputs": {
            "prompt": "counterfactual fixture",
            "params": {},
        },
        "artifacts": [
            _artifact(chunk_id, evidence[chunk_id])
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


def _write_base_source(tmp_path: Path) -> Path:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    sealed = finalize(
        _bundle(),
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


def _materialize_task(tmp_path: Path, fixture_name: str) -> dict:
    task = _task_fixture(fixture_name)
    task["base"]["source"]["path"] = str(_write_base_source(tmp_path).as_posix())
    task["task_id"] = compute_task_id(task)
    return task


def test_compute_counterfactual_task_id_excludes_task_id_from_hash():
    task = _task_fixture("counterfactual_task_remove_event.json")
    task["task_id"] = ""
    first = compute_counterfactual_task_id(task)
    task["task_id"] = "cf:" + ("0" * 64)
    second = compute_counterfactual_task_id(task)

    assert first == second


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


def _normalize_narrative(
    text: str,
    *,
    task_id: str,
    base_path: str,
    run_dir: str,
) -> str:
    return (
        text.replace(task_id, "FIXTURE_TASK_ID")
        .replace(base_path, "FIXTURE_BASE_OUTPUT_PATH")
        .replace(run_dir, "FIXTURE_COUNTERFACTUAL_PATH")
    )


def test_counterfactual_same_task_twice_is_byte_identical(tmp_path: Path):
    task = _materialize_task(tmp_path, "counterfactual_task_remove_event.json")
    out_dir = tmp_path / "out"

    first = run_counterfactual_task(task, out_dir=str(out_dir))
    second = run_counterfactual_task(task, out_dir=str(out_dir))

    assert first["run_dir"] == second["run_dir"]
    assert first["output_bytes"] == second["output_bytes"]
    assert first["attestation_bytes"] == second["attestation_bytes"]
    assert first["result_bytes"] == second["result_bytes"]


def test_counterfactual_remove_event_matches_expected_fixture(tmp_path: Path):
    task = _materialize_task(tmp_path, "counterfactual_task_remove_event.json")
    result = run_counterfactual_task(task, out_dir=str(tmp_path / "out"))
    expected = json.loads(
        (FIXTURES / "counterfactual_result_expected.json").read_text(encoding="utf-8")
    )

    assert _normalize_result(result["result"]) == expected
    assert result["counterfactual_output"]["world_model"]["events"] == [
        event
        for event in _base_output()["world_model"]["events"]
        if event["event_id"] != task["operation"]["target_id"]
    ]
    assert result["counterfactual_output"]["causal_graph"]["causal_order"] == [
        "event:" + ("1" * 64),
        "event:" + ("2" * 64),
    ]
    assert result["result"]["effects"]["verification_change"] == {
        "old": "VERIFIED_NEEDS_INFO",
        "new": "VERIFIED_OK",
    }


def test_counterfactual_remove_entity_updates_events_and_unknowns(tmp_path: Path):
    task = _materialize_task(tmp_path, "counterfactual_task_remove_entity.json")
    result = run_counterfactual_task(task, out_dir=str(tmp_path / "out"))

    assert len(result["counterfactual_output"]["world_model"]["entities"]) == 1
    assert all(
        task["operation"]["target_id"] not in event["objects"]
        for event in result["counterfactual_output"]["world_model"]["events"]
    )
    assert result["result"]["effects"]["changed_events"] == [
        {
            "event_id": "event:" + ("1" * 64),
            "fields_changed": ["objects"],
        },
        {
            "event_id": "event:" + ("2" * 64),
            "fields_changed": ["objects"],
        },
        {
            "event_id": "event:" + ("3" * 64),
            "fields_changed": ["objects"],
        },
    ]
    assert result["result"]["effects"]["changed_unknowns_count"]["new"] > result[
        "result"
    ]["effects"]["changed_unknowns_count"]["old"]
    assert result["result"]["effects"]["verification_change"]["new"] == (
        "VERIFIED_NEEDS_INFO"
    )


def test_counterfactual_narrative_matches_golden_fixture(tmp_path: Path):
    task = _materialize_task(tmp_path, "counterfactual_task_remove_event.json")
    result = run_counterfactual_task(task, out_dir=str(tmp_path / "out"))
    expected = (FIXTURES / "counterfactual_narrative_expected.txt").read_text(
        encoding="utf-8"
    )
    actual = _normalize_narrative(
        result["narrative"]["text"],
        task_id=task["task_id"],
        base_path=task["base"]["source"]["path"],
        run_dir=result["run_dir"],
    )

    assert actual == expected
    assert "\r" not in result["narrative"]["text"]
