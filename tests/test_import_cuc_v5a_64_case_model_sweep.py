from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


def _diag_assertion(
    *,
    case_id: str,
    source_case_id: str,
    bucket: str,
    run2a_pass: bool,
    run2a_score: float,
    run2b_pass: bool,
    run2b_score: float,
    citation_key_delta: int,
    citation_coverage_delta: float,
) -> dict[str, object]:
    payload = {
        "case_id": case_id,
        "source_case_id": source_case_id,
        "v5a_pilot_bucket": bucket,
        "run2a_overall_pass": run2a_pass,
        "run2a_overall_score": run2a_score,
        "run2b_overall_pass": run2b_pass,
        "run2b_overall_score": run2b_score,
        "diagnostics": {
            "run2a_citation_key_count": 8,
            "run2b_citation_key_count": 8 + citation_key_delta,
            "citation_key_delta": citation_key_delta,
            "run2a_obligation_coverage": 0.8,
            "run2b_obligation_coverage": 0.8 + citation_coverage_delta,
            "citation_coverage_delta": citation_coverage_delta,
            "prior_anchor_suspected": citation_key_delta >= 2
            or citation_coverage_delta >= 0.15,
        },
    }
    return {
        "id": f"diag-{case_id}",
        "passed": True,
        "expectation": "V5A_PRIOR_ANCHOR_DIAGNOSTICS=" + json.dumps(payload, sort_keys=True),
    }


def _run_record(
    *,
    case_id: str,
    family_id: str,
    sector_skin: str,
    render_profile: str,
    hop_depth: int,
    bucket: str,
    source_case_id: str,
    model_slug: str,
    run2a_pass: bool,
    run2a_score: float,
    run2b_pass: bool,
    run2b_score: float,
    citation_key_delta: int,
    citation_coverage_delta: float,
) -> dict[str, object]:
    return {
        "id": f"Run {case_id}",
        "param_id": 1,
        "case_id": case_id,
        "source_case_id": source_case_id,
        "family_id": family_id,
        "v5a_pilot_bucket": bucket,
        "sector_skin": sector_skin,
        "render_profile": render_profile,
        "hop_depth": hop_depth,
        "named_evidence_artifact": "evidence:test",
        "llm": model_slug,
        "passed": bool(run2a_pass and run2b_pass),
        "result": bool(run2a_pass and run2b_pass),
        "status": "success",
        "start_time": "2026-04-13T17:00:00Z",
        "end_time": "2026-04-13T17:00:10Z",
        "error_message": None,
        "assertion_results": [
            _diag_assertion(
                case_id=case_id,
                source_case_id=source_case_id,
                bucket=bucket,
                run2a_pass=run2a_pass,
                run2a_score=run2a_score,
                run2b_pass=run2b_pass,
                run2b_score=run2b_score,
                citation_key_delta=citation_key_delta,
                citation_coverage_delta=citation_coverage_delta,
            )
        ],
    }


def _write_v5a_zip(
    path: Path,
    *,
    exported_at_utc: str,
    model_slug: str,
    runs: list[dict[str, object]],
) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "cuc_v5a_candidate_export/results_export.json",
            json.dumps(
                {
                    "task_name": "cuc_metacognition_v5a_candidate",
                    "task_json_relative_path": "cuc_metacognition_v5a_candidate.task.json",
                    "params_json_relative_path": "cuc_v5_64_params.json",
                    "resolved_task_json_path": "/kaggle/input/foo/cuc_metacognition_v5a_candidate.task.json",
                    "resolved_params_json_path": "/kaggle/input/foo/cuc_v5_64_params.json",
                    "exported_at_utc": exported_at_utc,
                    "case_count": len(runs),
                    "run_count": len(runs),
                    "pass_count": sum(1 for run in runs if run["passed"]),
                    "fail_count": sum(1 for run in runs if not run["passed"]),
                    "results_repr": "Runs(...)",
                    "runs": runs,
                }
            ),
        )


def test_import_cuc_v5a_64_case_model_sweep_builds_combined_artifacts(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    zip_a = tmp_path / "results_a.zip"
    zip_a_old = tmp_path / "results_a_old.zip"
    zip_b = tmp_path / "results_b.zip"
    output_dir = tmp_path / "out"
    doc_dir = tmp_path / "docs"
    prefix = "cuc_v5a_64_case_sweep_2026_04_14_test"

    gpt_runs = [
        _run_record(
            case_id="CUCV5-CASE-01",
            family_id="threshold_crossing",
            sector_skin="security_incident",
            render_profile="incident_digest_v1",
            hop_depth=2,
            bucket="grounding_heavy",
            source_case_id="SRC-01",
            model_slug="openai/gpt-5.4-2026-03-05",
            run2a_pass=True,
            run2a_score=1.0,
            run2b_pass=False,
            run2b_score=0.5,
            citation_key_delta=4,
            citation_coverage_delta=0.2,
        ),
        _run_record(
            case_id="CUCV5-CASE-02",
            family_id="evidence_removal",
            sector_skin="legal_contract",
            render_profile="legal_formal_v1",
            hop_depth=3,
            bucket="propagation_heavy",
            source_case_id="SRC-02",
            model_slug="openai/gpt-5.4-2026-03-05",
            run2a_pass=False,
            run2a_score=0.3,
            run2b_pass=False,
            run2b_score=0.3,
            citation_key_delta=1,
            citation_coverage_delta=0.0,
        ),
    ]
    claude_runs = [
        _run_record(
            case_id="CUCV5-CASE-01",
            family_id="threshold_crossing",
            sector_skin="security_incident",
            render_profile="incident_digest_v1",
            hop_depth=2,
            bucket="grounding_heavy",
            source_case_id="SRC-01",
            model_slug="anthropic/claude-sonnet-4-6@default",
            run2a_pass=True,
            run2a_score=1.0,
            run2b_pass=True,
            run2b_score=1.0,
            citation_key_delta=0,
            citation_coverage_delta=0.0,
        ),
        _run_record(
            case_id="CUCV5-CASE-02",
            family_id="evidence_removal",
            sector_skin="legal_contract",
            render_profile="legal_formal_v1",
            hop_depth=3,
            bucket="propagation_heavy",
            source_case_id="SRC-02",
            model_slug="anthropic/claude-sonnet-4-6@default",
            run2a_pass=False,
            run2a_score=0.2,
            run2b_pass=False,
            run2b_score=0.2,
            citation_key_delta=0,
            citation_coverage_delta=0.0,
        ),
    ]

    _write_v5a_zip(
        zip_a_old,
        exported_at_utc="2026-04-13T16:00:00Z",
        model_slug="openai/gpt-5.4-2026-03-05",
        runs=gpt_runs,
    )
    _write_v5a_zip(
        zip_a,
        exported_at_utc="2026-04-13T17:00:00Z",
        model_slug="openai/gpt-5.4-2026-03-05",
        runs=gpt_runs,
    )
    _write_v5a_zip(
        zip_b,
        exported_at_utc="2026-04-13T17:05:00Z",
        model_slug="anthropic/claude-sonnet-4-6@default",
        runs=claude_runs,
    )

    command = [
        sys.executable,
        "scripts/import_cuc_v5a_64_case_model_sweep.py",
        "--zip-path",
        str(zip_a_old),
        str(zip_a),
        str(zip_b),
        "--output-dir",
        str(output_dir),
        "--doc-dir",
        str(doc_dir),
        "--prefix",
        prefix,
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr

    flat_csv = output_dir / f"cuc_results_flat_{prefix}.csv"
    model_summary_csv = output_dir / f"{prefix}_model_summary.csv"
    case_matrix_csv = output_dir / f"{prefix}_case_matrix.csv"
    family_summary_csv = output_dir / f"{prefix}_family_summary.csv"
    headline_txt = output_dir / f"{prefix}_headline_metrics.txt"
    summary_doc = doc_dir / "CUC_V5A_64_CASE_SWEEP_2026_04_14.md"

    for path in (
        flat_csv,
        model_summary_csv,
        case_matrix_csv,
        family_summary_csv,
        headline_txt,
        summary_doc,
    ):
        assert path.is_file(), f"Expected generated artifact: {path}"

    with model_summary_csv.open(encoding="utf-8", newline="") as handle:
        model_rows = list(csv.DictReader(handle))
    assert len(model_rows) == 2
    gpt_row = next(row for row in model_rows if row["model"] == "GPT-5.4")
    assert gpt_row["run2a_pass_count"] == "1"
    assert gpt_row["run2b_pass_count"] == "0"
    assert gpt_row["scaffold_cases"] == "1"
    assert gpt_row["both_fail_cases"] == "1"

    with case_matrix_csv.open(encoding="utf-8", newline="") as handle:
        case_rows = {row["case_id"]: row for row in csv.DictReader(handle)}
    assert case_rows["CUCV5-CASE-01"]["task_pass_model_count"] == "1"
    assert case_rows["CUCV5-CASE-01"]["run2a_pass_model_count"] == "2"
    assert case_rows["CUCV5-CASE-01"]["run2b_pass_model_count"] == "1"
    assert case_rows["CUCV5-CASE-02"]["all_models_task_failed"] == "True"

    with family_summary_csv.open(encoding="utf-8", newline="") as handle:
        family_rows = {row["family_id"]: row for row in csv.DictReader(handle)}
    assert family_rows["evidence_removal"]["run2a_pass_count"] == "0"
    assert family_rows["evidence_removal"]["run2b_pass_count"] == "0"

    summary_text = summary_doc.read_text(encoding="utf-8")
    assert "Duplicate zips skipped: 1" in summary_text
    assert "Counterexample models where 2B beats 2A: none" in summary_text
    assert "`evidence_removal` is the universal hard family" in summary_text

    headline_text = headline_txt.read_text(encoding="utf-8")
    assert "Distinct imported models: 2" in headline_text
    assert "Duplicate zips ignored: 1" in headline_text
