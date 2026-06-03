from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.deepseek_phase3_diagnostic_retry import (
    RetryDeltaResult,
    build_retry_messages,
    request_retry_delta,
    run_diagnostic_retry,
)
from scripts.delta_gap_diagnostic import compare_deltas

from core.cuc_harness.deepseek_proposer import DeepSeekProposer, RevisionDelta

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


def test_build_retry_messages_appends_diagnostic_repair_payload() -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    rejected_delta = _build_rejected_delta(gold_delta)
    gap_report = compare_deltas(rejected_delta, gold_delta).to_dict()
    repair_instruction = {
        "candidate_kind": "repair_instruction",
        "failure_family": "GROUNDING_GAP",
        "target_operation_id": "multiple",
        "required_fields": {
            "supporting_evidence_map_required": {
                "scenario:primary": ["evidence:response"]
            }
        },
    }

    messages = build_retry_messages(
        proposer=DeepSeekProposer(api_key="test-key"),
        clean_pack=_read_json(FIXTURE_DIR / "clean_pack.json"),
        perturbed_pack=_read_json(FIXTURE_DIR / "perturbed_pack.json"),
        case_id=CASE_ID,
        strict_copy=False,
        baseline_delta=rejected_delta,
        baseline_verification={"accepted": False},
        baseline_gap=gap_report,
        repair_instruction=repair_instruction,
    )

    assert [message["role"] for message in messages] == ["system", "user"]
    user_prompt = messages[1]["content"]
    assert "DIAGNOSTIC_REPAIR_INSTRUCTION:" in user_prompt
    assert "BASELINE_REJECTED_DELTA:" in user_prompt
    assert '"failure_family": "GROUNDING_GAP"' in user_prompt
    assert "Apply only the repair_instruction target changes." in user_prompt
    assert "Copy every object in exact_expected_fragments exactly." in user_prompt


def test_request_retry_delta_preserves_successful_fallback_model(monkeypatch) -> None:
    proposer = DeepSeekProposer(
        api_key="test-key",
        model="deepseek-primary",
        fallback_model="deepseek-fallback",
    )
    expected_delta = RevisionDelta.model_validate(
        _read_json(FIXTURE_DIR / "expected_delta.json")
    )
    requested_models: list[str] = []

    def fake_request_delta(*, model: str, messages: list[dict[str, str]]):
        requested_models.append(model)
        assert messages == [{"role": "user", "content": "retry prompt"}]
        if model == "deepseek-primary":
            return proposer._failure(  # noqa: SLF001
                model=model,
                error_type="rate_limit",
                message="primary unavailable",
            )
        return expected_delta

    monkeypatch.setattr(proposer, "_request_delta", fake_request_delta)

    result = request_retry_delta(
        proposer,
        [{"role": "user", "content": "retry prompt"}],
    )

    assert isinstance(result, RetryDeltaResult)
    assert result.delta == expected_delta
    assert result.model == "deepseek-fallback"
    assert requested_models == ["deepseek-primary", "deepseek-fallback"]


def test_dry_run_writes_repair_instruction_without_live_api(tmp_path: Path) -> None:
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")
    rejected_delta = _build_rejected_delta(gold_delta)
    baseline_case_dir = tmp_path / "baseline" / CASE_ID
    baseline_case_dir.mkdir(parents=True)
    _write_json(baseline_case_dir / "model_delta.json", rejected_delta)
    _write_json(
        baseline_case_dir / "gap_report.json",
        compare_deltas(rejected_delta, gold_delta).to_dict(),
    )

    result = run_diagnostic_retry(
        case_id=CASE_ID,
        params_json=PARAMS_PATH,
        baseline_dir=tmp_path / "baseline",
        output_dir=tmp_path / "out",
        ledger_root=tmp_path / "ledger",
        proposer=DeepSeekProposer(api_key="test-key"),
        strict_copy=False,
        dry_run=True,
    )

    repair_path = Path(result["repair_instruction_path"])
    repair_instruction = _read_json(repair_path)
    exact_state = repair_instruction["required_fields"]["exact_expected_fragments"][
        "changed_states"
    ][0]
    assert result["retry"] == {"called": False, "reason": "dry_run"}
    assert result["baseline"]["accepted"] is False
    assert repair_instruction["failure_family"] == "GROUNDING_GAP"
    assert exact_state["id"] == "state:primary"
    assert exact_state["before"]["attributes"] == {
        "exception_active": False,
        "rule_version": "v1",
        "scope": "global",
    }
    assert exact_state["before"]["confidence_band"] == "medium"
    assert "scenario:primary" in (
        repair_instruction["required_fields"]["supporting_evidence_map_required"]
    )


def _build_rejected_delta(gold_delta: dict) -> dict:
    rejected = json.loads(json.dumps(gold_delta))
    rejected["supporting_evidence_map"].pop("scenario:primary", None)
    rejected["changed_states"] = [
        item for item in rejected["changed_states"] if item["id"] != "state:primary"
    ]
    return rejected


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
