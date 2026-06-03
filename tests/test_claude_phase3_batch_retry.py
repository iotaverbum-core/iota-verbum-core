from __future__ import annotations

import importlib.util
import json
import tempfile
from argparse import Namespace
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts import claude_phase3_batch_retry as batch
from scripts.claude_phase3_diagnostic_retry import classify_failure_family

from core.cuc_harness.verifier import DeltaVerificationResult, VerificationIssue

pytestmark = pytest.mark.timeout(30)


@pytest.fixture(autouse=True)
def _block_live_network_clients():
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "core.cuc_harness.claude_proposer.httpx.Client",
                side_effect=AssertionError("tests must not open live HTTP clients"),
            )
        )
        if importlib.util.find_spec("anthropic") is not None:
            stack.enter_context(
                patch(
                    "anthropic.Anthropic",
                    side_effect=AssertionError(
                        "tests must not instantiate Anthropic clients"
                    ),
                )
            )
        yield


def test_batch_discovery_finds_exactly_64_cases() -> None:
    specs = batch.discover_case_specs()

    assert len(specs) == 64
    assert len({spec.case_id for spec in specs}) == 64


def test_per_case_result_schema_for_accepted_and_rejected_outcomes() -> None:
    accepted = batch.normalize_case_result(
        {
            "case_id": "case:accepted",
            "source_case_id": "source:accepted",
            "fixture_dir": "fixtures/accepted",
            "diagnostic_class": "ACCEPTED",
            "baseline": {
                "accepted": True,
                "reasons": [],
                "reason_families": [],
                "gap_summary": {"similarity_score_percent": 100.0},
            },
            "retry": {"called": False, "ledger_committed": False},
        }
    )
    rejected = batch.normalize_case_result(
        {
            "case_id": "case:rejected",
            "source_case_id": "source:rejected",
            "fixture_dir": "fixtures/rejected",
            "baseline": {
                "accepted": False,
                "reasons": ["missing_supporting_evidence:state:primary"],
                "reason_families": ["missing_supporting_evidence"],
                "gap_summary": {"similarity_score_percent": 70.0},
            },
            "retry": {
                "called": True,
                "accepted": False,
                "json_valid": True,
                "reasons": ["missing_preserved_items:state:stable"],
                "reason_families": ["missing_preserved_items"],
                "gap_summary": {"similarity_score_percent": 80.0},
                "ledger_committed": False,
            },
        }
    )

    for result in (accepted, rejected):
        assert result["schema_version"].endswith(".case_result")
        assert isinstance(result["case_id"], str)
        assert isinstance(result["diagnostic_class"], str)
        assert result["diagnostic_class"]
        assert result["diagnostic_class"] != "UNCLASSIFIED"

    assert accepted["baseline_accepted"] is True
    assert accepted["retry_called"] is False
    assert rejected["baseline_accepted"] is False
    assert rejected["diagnostic_class"] == "GROUNDING_GAP"
    assert rejected["terminal_diagnostic_class"] == "PRESERVATION_BREACH"
    assert rejected["similarity_delta"] == 10.0


def test_batch_proof_schema_and_unrepaired_population() -> None:
    case_results = [
        {
            "case_id": "case:fixed",
            "baseline_accepted": False,
            "diagnostic_class": "GROUNDING_GAP",
            "retry_called": True,
            "retry_accepted": True,
            "retry_similarity": 98.0,
            "similarity_delta": 20.0,
            "ledger_committed": True,
            "terminal_diagnostic_class": None,
            "terminal_failure_reasons": [],
        },
        {
            "case_id": "case:unrepaired",
            "baseline_accepted": False,
            "diagnostic_class": "PRESERVATION_BREACH",
            "retry_called": True,
            "retry_accepted": False,
            "retry_similarity": 77.5,
            "similarity_delta": 2.5,
            "ledger_committed": False,
            "terminal_diagnostic_class": "PRESERVATION_BREACH",
            "terminal_failure_reasons": ["missing_preserved_items:state:x"],
        },
    ]

    proof = batch.build_batch_proof(
        case_results=case_results,
        run_date="2026_06_02",
        dry_run=False,
        params_json=Path("benchmark/cuc_v5_64_params.json"),
        output_dir=Path("out"),
        ledger_root=Path("out/ledger"),
        results_dir=Path("results"),
    )

    assert proof["schema_version"] == batch.SCHEMA_VERSION
    assert proof["total_cases"] == 2
    assert proof["retry_accepted"] == {"count": 1, "rate": 0.5}
    assert proof["ledger_commit_rate"] == 0.5
    assert proof["similarity_delta_distribution"]["median"] == 11.25
    assert proof["diagnostic_class_breakdown"]["UNCLASSIFIED"] == 0
    assert proof["unrepaired"] == [
        {
            "case_id": "case:unrepaired",
            "terminal_diagnostic_class": "PRESERVATION_BREACH",
            "similarity_score": 77.5,
            "terminal_failure_reasons": ["missing_preserved_items:state:x"],
        }
    ]


def test_diagnostic_classifier_raises_on_unclassified_input() -> None:
    verification = DeltaVerificationResult(
        accepted=False,
        issues=(VerificationIssue(family="brand_new_unknown_family"),),
    )

    with pytest.raises(ValueError, match="unclassified verifier reason families"):
        classify_failure_family(verification, {})


def test_dry_run_completes_without_live_api_calls(monkeypatch) -> None:
    def fail_if_called(**_kwargs):
        raise AssertionError("dry-run without baselines must not call Claude retry")

    monkeypatch.setattr(batch, "run_diagnostic_retry", fail_if_called)

    with _temporary_directory(prefix="iv-batch-") as raw_tmp:
        tmp_path = Path(raw_tmp)
        proof = batch.run_batch_retry(
            params_json=batch.DEFAULT_PARAMS_PATH,
            baseline_dir=tmp_path / "missing-baselines",
            output_dir=tmp_path / "out",
            ledger_root=tmp_path / "ledger",
            results_dir=tmp_path / "results",
            proof_dir=tmp_path / "proof",
            proposer_args=_proposer_args(),
            dry_run=True,
            run_date="2026_06_02",
        )

        assert proof["dry_run"] is True
        assert proof["total_cases"] == 64
        assert proof["baseline_accepted"] == {"count": 64, "rate": 1.0}
        assert proof["retry_attempted"] == {"count": 0, "rate": 0.0}
        assert len(list((tmp_path / "results").glob("*_retry_result.json"))) == 64


def test_batch_proof_sha_fields_are_hex_strings() -> None:
    proof = batch.build_batch_proof(
        case_results=[
            {
                "case_id": "case:accepted",
                "baseline_accepted": True,
                "diagnostic_class": "ACCEPTED",
                "retry_called": False,
                "retry_accepted": None,
                "retry_similarity": None,
                "similarity_delta": None,
                "ledger_committed": False,
                "terminal_diagnostic_class": None,
                "terminal_failure_reasons": [],
            }
        ],
        run_date="2026_06_02",
        dry_run=True,
        params_json=Path("benchmark/cuc_v5_64_params.json"),
        output_dir=Path("out"),
        ledger_root=Path("out/ledger"),
        results_dir=Path("results"),
    )

    with _temporary_directory(prefix="iv-batch-proof-") as raw_tmp:
        proof_path = Path(raw_tmp) / "proof.json"
        batch.write_batch_proof(proof_path, proof)
        written = json.loads(proof_path.read_text(encoding="utf-8"))

    for key in ("bundle_sha", "attestation_sha"):
        assert isinstance(written[key], str)
        assert len(written[key]) == 64
        int(written[key], 16)


def _proposer_args() -> Namespace:
    return Namespace(
        model="claude-test",
        fallback_model="",
        timeout_seconds=1.0,
        max_tokens=128,
        effort=None,
        strict_copy=False,
        rate_limit_retries=0,
        rate_limit_sleep_seconds=0.0,
    )


def _temporary_directory(prefix: str) -> tempfile.TemporaryDirectory[str]:
    sandbox_tmp = Path("C:/tmp")
    if sandbox_tmp.is_dir():
        return tempfile.TemporaryDirectory(prefix=prefix, dir=sandbox_tmp)
    return tempfile.TemporaryDirectory(prefix=prefix)
