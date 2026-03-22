"""Offline tests for the CUC benchmark utilities."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from benchmark.run_evaluation import (
    CASE_METADATA,
    METADATA_REQUIRED_KEYS,
    build_run1_prompt,
    build_run2_messages,
    build_run2_prompt,
    validate_metadata_record,
)
from benchmark.score_responses import (
    Q1_HEADER,
    Q2_HEADER,
    Q3_HEADER,
    SCORE_COLUMNS,
    SUMMARY_COLUMNS,
    parse_sections,
    score_case_response,
    write_scores,
)


def test_run_evaluation_dry_run_exits_zero_and_prints_expected_output() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "benchmark/run_evaluation.py",
            "--dry-run",
            "--cases",
            "DJI-2026-03-19-LIVE",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "CUC benchmark dry run" in completed.stdout
    assert "PLAN DJI-2026-03-19-LIVE gpt-4o run1" in completed.stdout
    assert "PLAN DJI-2026-03-19-LIVE gpt-4o run2" in completed.stdout


def test_score_responses_scores_synthetic_fixture(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    runs_dir = tmp_path / "runs"
    case_id = "DJI-2026-03-19-LIVE"
    case_dir = fixtures_dir / case_id
    run_dir = runs_dir / case_id
    case_dir.mkdir(parents=True)
    run_dir.mkdir(parents=True)

    diff_payload = {
        "domain": CASE_METADATA[case_id]["domain"],
        "perturbation_type": CASE_METADATA[case_id]["perturbation_type"],
        "changed_states": ["Exposure moved from LOW to HIGH"],
        "changed_edges": ["Liquidity stress now causes covenant breach risk"],
        "fired_invalidations": ["Base case invalidated by debt covenant trip"],
        "invalidated_scenarios": [
            {
                "original_conclusion": "Base case remains viable",
                "revision": "Base case no longer remains viable",
            }
        ],
        "resolved_unknowns": ["Unknown debt maturity date resolved to 2027-06-30"],
        "new_unknowns": ["Unknown waiver status introduced"],
    }
    response_text = "\n".join(
        [
            "Q1 DETECTION:",
            "- Exposure moved from LOW to HIGH",
            "- Liquidity stress now causes covenant breach risk",
            "- Base case invalidated by debt covenant trip",
            "Q2 SELF-CORRECTION:",
            (
                "- Original conclusion: Base case remains viable. "
                "Revision: Base case no longer remains viable."
            ),
            "Q3 UNKNOWN TRACKING:",
            "- Unknown debt maturity date resolved to 2027-06-30",
            "- Unknown waiver status introduced",
        ]
    )
    (case_dir / "diff.json").write_text(json.dumps(diff_payload), encoding="utf-8")
    (run_dir / "openai_gpt-4o_run2.txt").write_text(response_text, encoding="utf-8")

    output_path = tmp_path / "SCORES.csv"
    completed = subprocess.run(
        [
            sys.executable,
            "benchmark/score_responses.py",
            "--fixtures-dir",
            str(fixtures_dir),
            "--runs-dir",
            str(runs_dir),
            "--output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    rows = list(csv.DictReader(output_path.open(encoding="utf-8", newline="")))
    assert len(rows) == 1
    row = rows[0]
    assert row["domain"] == CASE_METADATA[case_id]["domain"]
    assert row["perturbation_type"] == CASE_METADATA[case_id]["perturbation_type"]
    assert row["q1_score"] == "9"
    assert row["q2_score"] == "3"
    assert row["q3_score"] == "6"
    assert row["total_score"] == "18"
    assert row["hallucination_count"] == "0"
    assert row["over_revision_count"] == "0"


def test_parse_sections_accepts_markdown_and_legacy_q_headers() -> None:
    markdown_response = "\n".join(
        [
            "## Q1 — DETECTION",
            "- state_003 changed from 21% to 28%",
            "## Q2 - SELF-CORRECTION",
            "- scen_A weakened because inv_002 is now active",
            "Q3: UNKNOWN TRACKING",
            "- unk_002 partially resolved",
        ]
    )
    markdown_sections = parse_sections(markdown_response)

    assert markdown_sections[Q1_HEADER] == "- state_003 changed from 21% to 28%"
    assert (
        markdown_sections[Q2_HEADER]
        == "- scen_A weakened because inv_002 is now active"
    )
    assert markdown_sections[Q3_HEADER] == "- unk_002 partially resolved"

    legacy_response = "\n".join(
        [
            "Q1 DETECTION:",
            "- edge_003 strength increased",
            "Q2 SELF-CORRECTION:",
            "- scen_A weakened",
        ]
    )
    legacy_sections = parse_sections(legacy_response)

    assert legacy_sections[Q1_HEADER] == "- edge_003 strength increased"
    assert legacy_sections[Q2_HEADER] == "- scen_A weakened"


def test_q2_scoring_matches_free_form_invalidated_scenario_strings() -> None:
    diff_payload = {
        "domain": CASE_METADATA["ALZHM-2026-PHASE3-TRIAL"]["domain"],
        "perturbation_type": CASE_METADATA["ALZHM-2026-PHASE3-TRIAL"][
            "perturbation_type"
        ],
        "changed_states": [],
        "changed_edges": [],
        "fired_invalidations": ["inv_002 threshold breached due to safety risk"],
        "invalidated_scenarios": [
            "scen_A weakened; REMS now more likely because ARIA-E crossed threshold"
        ],
        "resolved_unknowns": [],
        "new_unknowns": [],
    }
    response_text = "\n".join(
        [
            "## Q2 — SELF-CORRECTION",
            (
                "- scen_A weakened; REMS now more likely after inv_002 breached "
                "the safety threshold."
            ),
        ]
    )

    row = score_case_response(
        case_id="ALZHM-2026-PHASE3-TRIAL",
        diff_payload=diff_payload,
        model_slug="openai_gpt-4o",
        response_text=response_text,
        response_file=Path("benchmark/runs/ALZHM-2026-PHASE3-TRIAL/openai_gpt-4o_run2.txt"),
    )

    assert row["q2_score"] == 3
    assert row["over_revision_count"] == 0


def test_metadata_json_schema_validation_function() -> None:
    record = {
        "case_id": "DJI-2026-03-19-LIVE",
        "run": 1,
        "model_slug": "openai_gpt-4o",
        "model_version": "gpt-4o",
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "timestamp_utc": "2026-03-22T10:00:00.123456Z",
        "temperature": 0.0,
        "max_tokens": 2048,
        "api_latency_ms": 123,
    }

    validate_metadata_record(record)

    invalid = dict(record)
    invalid["run"] = 3
    with pytest.raises(ValueError):
        validate_metadata_record(invalid)

    assert tuple(record.keys()) == METADATA_REQUIRED_KEYS


def test_sorted_outputs_are_deterministic(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    for case_id in (
        "CLIMATE-2026-AMOC-TIPPING",
        "DJI-2026-03-19-LIVE",
        "NATO-2026-ARTICLE5-THRESHOLD",
    ):
        (fixtures_dir / case_id).mkdir(parents=True)

    from benchmark.run_evaluation import discover_case_ids as discover_run_cases
    from benchmark.score_responses import discover_case_ids as discover_score_cases

    expected = [
        "CLIMATE-2026-AMOC-TIPPING",
        "DJI-2026-03-19-LIVE",
        "NATO-2026-ARTICLE5-THRESHOLD",
    ]
    assert discover_run_cases(fixtures_dir) == expected
    assert discover_score_cases(fixtures_dir) == expected


def test_csv_output_columns_match_specification_exactly(tmp_path: Path) -> None:
    rows = [
        {
            "case_id": "DJI-2026-03-19-LIVE",
            "domain": CASE_METADATA["DJI-2026-03-19-LIVE"]["domain"],
            "perturbation_type": CASE_METADATA["DJI-2026-03-19-LIVE"][
                "perturbation_type"
            ],
            "model_slug": "openai_gpt-4o",
            "q1_score": 9,
            "q2_score": 3,
            "q3_score": 6,
            "total_score": 18,
            "hallucination_count": 0,
            "over_revision_count": 0,
            "run2_response_file": (
                "benchmark/runs/DJI-2026-03-19-LIVE/openai_gpt-4o_run2.txt"
            ),
            "scored_at_utc": "2026-03-22T10:00:00.123456Z",
        }
    ]
    output_path = tmp_path / "SCORES.csv"

    write_scores(rows, output_path)

    with output_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
    with output_path.with_name("SCORES_SUMMARY.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        summary_reader = csv.reader(handle)
        summary_header = next(summary_reader)
        summary_rows = list(summary_reader)

    assert tuple(header) == SCORE_COLUMNS
    assert tuple(summary_header) == SUMMARY_COLUMNS
    assert summary_rows[-1][0] == "Human Baseline"
    assert summary_rows[-1][-1] == "estimated from per-perturbation-type overall scores"


def test_run2_message_construction_uses_four_turn_context() -> None:
    system_prompt = "system"
    clean_text = "clean pack"
    run1_response = "run1 response"
    perturbed_text = "updated pack"

    messages = build_run2_messages(
        system_prompt=system_prompt,
        run1_user_prompt=build_run1_prompt(clean_text),
        run1_response_text=run1_response,
        run2_user_prompt=build_run2_prompt(perturbed_text),
    )

    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert messages[0]["content"] == system_prompt
    assert "=== EVIDENCE PACK ===" in messages[1]["content"]
    assert messages[2]["content"] == run1_response
    assert "=== UPDATED EVIDENCE PACK ===" in messages[3]["content"]
