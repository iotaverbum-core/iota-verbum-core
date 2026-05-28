from __future__ import annotations

import json
from pathlib import Path

from scripts.claude_cuc_24_production_probe import (
    EXPECTED_CASE_COUNT,
    SCHEMA_VERSION,
    build_dry_run_payload,
    build_proposer,
    default_ledger_root,
    load_case_specs,
    parse_args,
    run_production_matrix,
)

from core.cuc_harness.deepseek_proposer import RevisionDelta, SealedFailureArtifact


class GoldDeltaProposer:
    model = "fake-claude-gold"
    fallback_model = ""
    effort = None
    max_tokens = 8192
    rate_limit_retries = 5
    rate_limit_sleep_seconds = 70.0

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
        gold_delta = _read_json(fixture_dir / "expected_delta.json")
        return RevisionDelta.model_validate(gold_delta)


class AuthErrorProposer:
    model = "fake-claude-error"
    fallback_model = ""
    effort = None
    max_tokens = 8192
    rate_limit_retries = 5
    rate_limit_sleep_seconds = 70.0

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
            failure_id="sealed-failure:test-claude-24",
            provider="claude",
            model=self.model,
            endpoint="https://api.anthropic.com/v1/messages",
            error_type="api_error",
            message="Claude API returned HTTP 401.",
            status_code=401,
            response_body={"error": {"type": "authentication_error"}},
        )


def test_load_case_specs_defaults_to_v4_24_fixture_set() -> None:
    specs = load_case_specs()

    assert len(specs) == EXPECTED_CASE_COUNT
    assert specs[0].case_id == "CUCV4-PRESERVE-01-SIBLING-STABILITY-LEGAL-CONTRACT"
    assert specs[-1].case_id == "CUCV4-CORE-09-EXCEPTION-ACTIVATION-SECURITY-INCIDENT"
    for spec in specs:
        assert (spec.fixture_dir / "clean_pack.json").is_file()
        assert (spec.fixture_dir / "perturbed_pack.json").is_file()
        assert (spec.fixture_dir / "expected_delta.json").is_file()
    invariant_01 = _fixture_by_case_id()[
        "CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT"
    ]
    assert _expected_scenario_rank_changes(invariant_01) == (
        _actual_scenario_rank_changes(invariant_01)
    )


def test_dry_run_payload_lists_cases_without_instantiating_proposer(tmp_path: Path) -> None:
    specs = load_case_specs(limit=2)
    output_dir = tmp_path / "out"

    payload = build_dry_run_payload(
        specs=specs,
        params_path=Path("benchmark/cuc_v4_candidate_params.json"),
        output_dir=output_dir,
        ledger_root=default_ledger_root(output_dir),
    )

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["case_count"] == 2
    assert payload["ledger_root"] == (output_dir / "ledger").as_posix()


def test_build_proposer_passes_rate_limit_configuration() -> None:
    args = parse_args(
        [
            "--rate-limit-retries",
            "7",
            "--rate-limit-sleep-seconds",
            "91",
            "--model",
            "claude-sonnet-4-6",
            "--fallback-model",
        ]
    )

    proposer = build_proposer(args)

    assert proposer.model == "claude-sonnet-4-6"
    assert proposer.fallback_model == ""
    assert proposer.rate_limit_retries == 7
    assert proposer.rate_limit_sleep_seconds == 91.0


def test_production_matrix_with_gold_proposer_commits_24_cases(
    tmp_path: Path,
) -> None:
    payload = run_production_matrix(
        specs=load_case_specs(),
        proposer=GoldDeltaProposer(),
        output_dir=tmp_path / "out",
        ledger_root=tmp_path / "out" / "ledger",
        strict_copy=False,
    )

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["summary"]["case_count"] == EXPECTED_CASE_COUNT
    assert payload["summary"]["json_valid_count"] == EXPECTED_CASE_COUNT
    assert payload["summary"]["verifier_accepted_count"] == EXPECTED_CASE_COUNT
    assert payload["summary"]["ledger_committed_count"] == EXPECTED_CASE_COUNT
    assert payload["summary"]["ledger_commit_rate"] == 1.0
    assert all(result["ledger_committed"] for result in payload["results"])
    assert (tmp_path / "out" / "summary.json").is_file()


def test_production_matrix_auth_failure_aborts_without_ledger_commit(
    tmp_path: Path,
) -> None:
    payload = run_production_matrix(
        specs=load_case_specs(limit=2),
        proposer=AuthErrorProposer(),
        output_dir=tmp_path / "out",
        ledger_root=tmp_path / "out" / "ledger",
        strict_copy=False,
    )

    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["aborted_reason"] == "authentication_failed"
    assert payload["summary"]["ledger_committed_count"] == 0
    assert payload["results"][0]["ledger_committed"] is False


def _fixture_by_case_id() -> dict[str, Path]:
    return {spec.case_id: spec.fixture_dir for spec in load_case_specs()}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _expected_scenario_rank_changes(fixture_dir: Path) -> list[dict]:
    return sorted(
        _read_json(fixture_dir / "expected_delta.json")["scenario_rank_changes"],
        key=lambda item: item["scenario_id"],
    )


def _actual_scenario_rank_changes(fixture_dir: Path) -> list[dict]:
    clean_ranks = _scenario_ranks(_read_json(fixture_dir / "clean_pack.json"))
    perturbed_ranks = _scenario_ranks(_read_json(fixture_dir / "perturbed_pack.json"))
    changes = []
    for scenario_id in sorted(set(clean_ranks) | set(perturbed_ranks)):
        before_rank = clean_ranks.get(scenario_id)
        after_rank = perturbed_ranks.get(scenario_id)
        if before_rank == after_rank:
            continue
        changes.append(
            {
                "after_rank": after_rank,
                "before_rank": before_rank,
                "scenario_id": scenario_id,
            }
        )
    return changes


def _scenario_ranks(pack: dict) -> dict[str, int | None]:
    return {
        item["scenario_id"]: item.get("rank")
        for item in pack["sections"]["scenarios"]
        if isinstance(item, dict) and isinstance(item.get("scenario_id"), str)
    }
