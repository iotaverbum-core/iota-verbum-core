from __future__ import annotations

import json
from pathlib import Path

from scripts.claude_cuc_smoke_matrix import parse_args, run_smoke_matrix
from scripts.deepseek_cuc_smoke_matrix import load_case_specs

from core.cuc_harness.deepseek_proposer import RevisionDelta, SealedFailureArtifact


class GoldDeltaProposer:
    model = "fake-claude-gold"
    fallback_model = ""
    effort = None
    max_tokens = 8192

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


class AuthErrorProposer:
    model = "fake-claude-error"
    fallback_model = ""
    effort = None
    max_tokens = 8192

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
            failure_id="sealed-failure:test-claude",
            provider="claude",
            model="fake-claude-error",
            endpoint="https://api.anthropic.com/v1/messages",
            error_type="api_error",
            message="Claude API returned HTTP 401.",
            status_code=401,
            response_body={"error": {"type": "authentication_error"}},
        )


def test_claude_smoke_matrix_with_gold_proposer_accepts_all_cases(
    tmp_path: Path,
) -> None:
    payload = run_smoke_matrix(
        specs=load_case_specs(),
        proposer=GoldDeltaProposer(),
        output_dir=tmp_path,
        strict_copy=False,
    )

    assert payload["schema_version"] == "iv.cuc_harness.claude_smoke_matrix.v1"
    assert payload["summary"]["case_count"] == 5
    assert payload["summary"]["json_valid_count"] == 5
    assert payload["summary"]["verifier_accepted_count"] == 5
    assert payload["summary"]["acceptance_rate"] == 1.0
    assert (tmp_path / "summary.json").is_file()


def test_claude_smoke_matrix_aborts_after_auth_failure(tmp_path: Path) -> None:
    payload = run_smoke_matrix(
        specs=load_case_specs(),
        proposer=AuthErrorProposer(),
        output_dir=tmp_path,
        strict_copy=False,
    )

    assert payload["summary"]["requested_case_count"] == 5
    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["aborted_reason"] == "authentication_failed"


def test_claude_fallback_model_flag_accepts_empty_value() -> None:
    args = parse_args(["--fallback-model"])

    assert args.fallback_model == ""


def _fixture_by_case_id() -> dict[str, Path]:
    return {spec.case_id: spec.fixture_dir for spec in load_case_specs()}
