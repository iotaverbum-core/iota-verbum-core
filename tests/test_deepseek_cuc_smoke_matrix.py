from __future__ import annotations

import json
from pathlib import Path

from scripts.deepseek_cuc_smoke_matrix import (
    DEFAULT_CASE_IDS,
    load_case_specs,
    parse_args,
    run_case,
    run_smoke_matrix,
    verify_delta_against_gold,
)

from core.cuc_harness.deepseek_proposer import RevisionDelta, SealedFailureArtifact


class GoldDeltaProposer:
    model = "fake-gold"
    fallback_model = ""

    def propose(
        self,
        clean_pack,
        perturbed_pack,
        *,
        case_id: str = "",
        strict_copy: bool = False,
    ) -> RevisionDelta:
        del clean_pack, perturbed_pack, strict_copy
        fixture_dir = _fixture_by_case_id()[case_id]
        gold_delta = json.loads(
            (fixture_dir / "expected_delta.json").read_text(encoding="utf-8")
        )
        return RevisionDelta.model_validate(gold_delta)


class ApiErrorProposer:
    model = "fake-error"
    fallback_model = ""

    def propose(
        self,
        clean_pack,
        perturbed_pack,
        *,
        case_id: str = "",
        strict_copy: bool = False,
    ) -> SealedFailureArtifact:
        del clean_pack, perturbed_pack, case_id, strict_copy
        return SealedFailureArtifact(
            schema_version="iv.cuc_harness.sealed_failure.v1",
            failure_id="sealed-failure:test",
            provider="deepseek",
            model="fake-error",
            endpoint="https://api.deepseek.com/v1/chat/completions",
            error_type="api_error",
            message="DeepSeek API returned HTTP 401.",
            status_code=401,
            response_body={"error": {"message": "Unauthorized"}},
        )


def test_load_case_specs_defaults_to_five_case_smoke_matrix() -> None:
    specs = load_case_specs()

    assert [spec.case_id for spec in specs] == DEFAULT_CASE_IDS
    assert len(specs) == 5
    for spec in specs:
        assert (spec.fixture_dir / "clean_pack.json").is_file()
        assert (spec.fixture_dir / "perturbed_pack.json").is_file()
        assert (spec.fixture_dir / "expected_delta.json").is_file()


def test_verify_delta_accepts_gold_delta_for_default_cases() -> None:
    for spec in load_case_specs():
        gold_delta = json.loads(
            (spec.fixture_dir / "expected_delta.json").read_text(encoding="utf-8")
        )
        proposal = RevisionDelta.model_validate(gold_delta)

        accepted, reasons = verify_delta_against_gold(proposal, gold_delta)

        assert accepted
        assert reasons == []


def test_smoke_matrix_with_gold_proposer_accepts_all_cases(tmp_path: Path) -> None:
    payload = run_smoke_matrix(
        specs=load_case_specs(),
        proposer=GoldDeltaProposer(),
        output_dir=tmp_path,
        strict_copy=False,
        ledger_root=tmp_path / "ledger",
    )

    assert payload["summary"]["case_count"] == 5
    assert payload["summary"]["json_valid_count"] == 5
    assert payload["summary"]["verifier_accepted_count"] == 5
    assert payload["summary"]["ledger_committed_count"] == 5
    assert payload["summary"]["acceptance_rate"] == 1.0
    assert payload["summary"]["ledger_commit_rate"] == 1.0
    assert all(
        result["verifier_reason_families"] == [] for result in payload["results"]
    )
    assert all(result["ledger_committed"] for result in payload["results"])
    assert (tmp_path / "summary.json").is_file()


def test_smoke_matrix_result_includes_api_failure_details(tmp_path: Path) -> None:
    result = run_case(
        spec=load_case_specs(case_ids=[DEFAULT_CASE_IDS[0]])[0],
        proposer=ApiErrorProposer(),
        output_dir=tmp_path,
        strict_copy=False,
    )

    assert result["json_valid"] is False
    assert result["failure"]["status_code"] == 401
    assert result["failure"]["response_body"] == {
        "error": {"message": "Unauthorized"}
    }
    assert (tmp_path / DEFAULT_CASE_IDS[0] / "failure.json").is_file()


def test_smoke_matrix_aborts_after_auth_failure(tmp_path: Path) -> None:
    payload = run_smoke_matrix(
        specs=load_case_specs(),
        proposer=ApiErrorProposer(),
        output_dir=tmp_path,
        strict_copy=False,
    )

    assert payload["summary"]["requested_case_count"] == 5
    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["aborted_reason"] == "authentication_failed"


def test_fallback_model_flag_accepts_empty_value() -> None:
    args = parse_args(["--fallback-model"])

    assert args.fallback_model == ""


def _fixture_by_case_id() -> dict[str, Path]:
    return {spec.case_id: spec.fixture_dir for spec in load_case_specs()}
