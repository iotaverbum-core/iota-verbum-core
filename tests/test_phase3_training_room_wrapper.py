from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.delta_gap_diagnostic import compare_deltas
from scripts.phase3_training_room_wrapper import (
    TrainingRoomRequest,
    load_baseline_candidate,
    run_training_room_session,
)

pytestmark = pytest.mark.timeout(30)

CASE_ID = "CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
SOURCE_CASE_ID = "CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
FIXTURE_DIR = Path("benchmark/kaggle/fixtures") / SOURCE_CASE_ID
PARAMS_PATH = Path("benchmark/cuc_v5a_candidate_params.json")


@pytest.fixture(autouse=True)
def _block_live_http_clients():
    with patch(
        "core.cuc_harness.deepseek_proposer.httpx.Client",
        side_effect=AssertionError("tests must not open live HTTP clients"),
    ):
        yield


def test_load_baseline_candidate_scores_failed_benchmark(tmp_path: Path) -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    rejected_delta = _build_rejected_delta(gold_delta)
    baseline_dir = _write_baseline(tmp_path, rejected_delta, gold_delta)

    baseline = load_baseline_candidate(
        case_id=CASE_ID,
        baseline_dir=baseline_dir,
        expected_delta=gold_delta,
    )

    assert baseline["accepted"] is False
    assert baseline["similarity_score_percent"] < 100.0
    assert baseline["verifier_reason_count"] > 0
    assert "missing_changed_states" in baseline["verifier_reason_families"]


def test_training_room_plans_retry_without_live_model(tmp_path: Path) -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    rejected_delta = _build_rejected_delta(gold_delta)
    baseline_dir = _write_baseline(tmp_path, rejected_delta, gold_delta)

    scorecard = run_training_room_session(
        TrainingRoomRequest(
            provider="deepseek",
            case_id=CASE_ID,
            params_json=PARAMS_PATH,
            baseline_dir=baseline_dir,
            output_dir=tmp_path / "out",
            max_training_passes=1,
            allow_live_model=False,
            model="deepseek-v4-pro",
            fallback_model="",
        )
    )

    assert scorecard["stop_reason"] == "live_model_not_enabled"
    assert scorecard["baseline"]["accepted"] is False
    assert scorecard["training_passes"][0]["called"] is False
    assert scorecard["best_candidate"]["label"] == "baseline"
    assert Path(scorecard["artifacts"]["scorecard_path"]).is_file()


def test_training_room_imports_accepted_retry_as_best(tmp_path: Path) -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    rejected_delta = _build_rejected_delta(gold_delta)
    baseline_dir = _write_baseline(tmp_path, rejected_delta, gold_delta)
    training_dir = tmp_path / "accepted_pass" / CASE_ID
    training_dir.mkdir(parents=True)
    _write_json(
        training_dir / "training_summary.json",
        {
            "case_id": CASE_ID,
            "baseline": {
                "accepted": False,
                "gap_summary": compare_deltas(rejected_delta, gold_delta).to_dict()[
                    "summary"
                ],
                "reason_families": ["mismatched_changed_states"],
                "reasons": ["mismatched_changed_states:state:primary"],
            },
            "retry": {
                "accepted": True,
                "called": True,
                "gap_summary": {
                    "compared_fields": 91,
                    "matching_fields": 91,
                    "similarity_score_percent": 100.0,
                },
                "json_valid": True,
                "ledger_commit": {
                    "bundle_sha256": "1" * 64,
                    "output_sha256": "2" * 64,
                    "attestation_sha256": "3" * 64,
                    "run_dir": "ledger/" + "1" * 64,
                },
                "ledger_committed": True,
                "model_delta_path": "retry_model_delta.json",
                "gap_report_path": "retry_gap_report.json",
                "reason_families": [],
                "reasons": [],
            },
            "training_effect": {
                "accepted_after": True,
                "accepted_before": False,
                "improved": True,
            },
        },
    )

    scorecard = run_training_room_session(
        TrainingRoomRequest(
            provider="deepseek",
            case_id=CASE_ID,
            params_json=PARAMS_PATH,
            baseline_dir=baseline_dir,
            output_dir=tmp_path / "out",
            training_dirs=(tmp_path / "accepted_pass",),
            model="deepseek-v4-pro",
            fallback_model="",
        )
    )

    assert scorecard["stop_reason"] == "no_training_requested"
    assert scorecard["best_candidate"]["accepted"] is True
    assert scorecard["best_candidate"]["ledger_committed"] is True
    assert scorecard["training_effect"]["accepted_after"] is True
    assert scorecard["training_effect"]["improved"] is True


def _build_rejected_delta(gold_delta: dict) -> dict:
    rejected = json.loads(json.dumps(gold_delta))
    rejected["changed_states"] = [
        item for item in rejected["changed_states"] if item["id"] != "state:primary"
    ]
    rejected["supporting_evidence_map"].pop("scenario:primary", None)
    return rejected


def _write_baseline(
    tmp_path: Path,
    rejected_delta: dict,
    gold_delta: dict,
) -> Path:
    baseline_case_dir = tmp_path / "baseline" / CASE_ID
    baseline_case_dir.mkdir(parents=True)
    _write_json(baseline_case_dir / "model_delta.json", rejected_delta)
    _write_json(
        baseline_case_dir / "gap_report.json",
        compare_deltas(rejected_delta, gold_delta).to_dict(),
    )
    return tmp_path / "baseline"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
