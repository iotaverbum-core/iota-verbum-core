from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


def _assertion(*, expectation: str, passed: bool = True) -> dict[str, object]:
    return {
        "expectation": expectation,
        "status": "BENCHMARK_ASSERTION_STATUS_PASSED"
        if passed
        else "BENCHMARK_ASSERTION_STATUS_FAILED",
    }


def _build_run_payload(case_id: str) -> dict[str, object]:
    assertions = [
        _assertion(expectation=f"{case_id} should return one judge result per criterion."),
        _assertion(expectation=f"{case_id} should pass at least 11 of 15 criteria."),
    ]
    assertions.extend(
        _assertion(expectation=f"{case_id} criterion {index}/15 should pass: synthetic criterion")
        for index in range(1, 16)
    )
    return {
        "modelVersion": {"slug": "google/gemini-2.5-flash"},
        "results": [{"booleanResult": True}],
        "assertions": assertions,
        "startTime": "2026-03-31T19:00:00Z",
        "endTime": "2026-03-31T19:00:05Z",
        "state": "BENCHMARK_TASK_RUN_STATE_COMPLETED",
    }


def _v4_assertion(*, expectation: str, passed: bool = True) -> dict[str, object]:
    return {
        "expectation": expectation,
        "status": "BENCHMARK_TASK_RUN_ASSERTION_STATUS_PASSED"
        if passed
        else "BENCHMARK_TASK_RUN_ASSERTION_STATUS_FAILED",
    }


def _build_v4_run_payload(
    case_id: str,
    *,
    model_slug: str = "openai/gpt-5.4-2026-03-05",
    overall_pass: bool = True,
    overall_score: float = 0.82,
    hard_fail_reasons: list[str] | None = None,
) -> dict[str, object]:
    hard_fail_reasons = hard_fail_reasons or []
    score = {
        "hard_fail_reasons": hard_fail_reasons,
        "axis_scores": {
            "delta_detection": 1.0,
            "causal_temporal_propagation": 0.8,
            "selective_revision": 1.0,
            "unknown_ledger_discipline": 1.0,
            "evidence_grounding": 1.0,
        },
        "overall_score": overall_score,
        "overall_pass": overall_pass,
    }
    assertions = [
        _v4_assertion(
            expectation=f"{case_id} should avoid hard fails around changed artifact Artifact-X: {hard_fail_reasons}",
            passed=not hard_fail_reasons,
        ),
        _v4_assertion(
            expectation=f"{case_id} should detect the revised branch ['state:x']. axis_scores={score['axis_scores']}",
            passed=True,
        ),
        _v4_assertion(
            expectation=f"{case_id} should ground its revisions in Artifact-X. axis_scores={score['axis_scores']}",
            passed=True,
        ),
        _v4_assertion(
            expectation=f"{case_id} should preserve stable sibling claims ['state:y'] while revising only impacted claims. axis_scores={score['axis_scores']}",
            passed=True,
        ),
        _v4_assertion(
            expectation=f"{case_id} should propagate the revision through dependent claims. causal_chain={{'chain': ['C1']}} axis_scores={score['axis_scores']}",
            passed=True,
        ),
        _v4_assertion(
            expectation=f"{case_id} should satisfy the v4 candidate structured pass rule. family_id=test render_profile=test hop_depth=2 named_evidence_artifact=Artifact-X score={score}",
            passed=overall_pass,
        ),
    ]
    return {
        "taskVersion": {"versionNumber": 1, "name": "cuc_metacognition_v4_candidate"},
        "modelVersion": {"slug": model_slug},
        "results": [{"booleanResult": overall_pass}],
        "assertions": assertions,
        "startTime": "2026-04-08T19:11:02Z",
        "endTime": "2026-04-08T19:11:37Z",
        "state": "BENCHMARK_TASK_RUN_STATE_COMPLETED",
    }


def test_import_cuc_kaggle_results_accepts_results_directory(tmp_path: Path) -> None:
    results_dir = tmp_path / "results_source"
    results_dir.mkdir()
    (results_dir / "cuc_metacognition_legal_v2.task.json").write_text(
        json.dumps({"name": "cuc_metacognition_legal_v2"}),
        encoding="utf-8",
    )
    (results_dir / "cuc_metacognition_legal_v2-run_param_id_0_google_gemini-2.5-flash.run.json").write_text(
        json.dumps(_build_run_payload("EPA-2026-HALCYON-SUPERFUND")),
        encoding="utf-8",
    )

    output_dir = tmp_path / "out"
    doc_dir = tmp_path / "docs"
    prefix = "folder_import_smoke"
    command = [
        sys.executable,
        "scripts/import_cuc_kaggle_results_zip.py",
        "--results-dir",
        str(results_dir),
        "--output-dir",
        str(output_dir),
        "--doc-dir",
        str(doc_dir),
        "--prefix",
        prefix,
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0

    flat_csv = output_dir / f"cuc_results_flat_{prefix}.csv"
    case_matrix = output_dir / f"{prefix}_case_matrix.csv"
    headline = output_dir / f"{prefix}_headline_metrics.txt"
    summary = output_dir / f"{prefix}_summary.txt"
    findings = doc_dir / f"CUC_findings_{prefix}.md"

    for path in (flat_csv, case_matrix, headline, summary, findings):
        assert path.is_file(), f"Expected generated artifact: {path}"

    with flat_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["case_id"] == "EPA-2026-HALCYON-SUPERFUND"
    assert rows[0]["model"] == "Gemini 2.5 Flash"
    assert rows[0]["criteria_passed"] == "15"

    headline_text = headline.read_text(encoding="utf-8")
    summary_text = summary.read_text(encoding="utf-8")
    findings_text = findings.read_text(encoding="utf-8")
    assert "results_source" in headline_text
    assert "Authoritative source: " in summary_text
    assert "Authoritative source: `results_source`" in findings_text


def test_import_cuc_kaggle_results_accepts_v4_candidate_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / "v4_results.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "cuc_metacognition_v4_candidate.task.json",
            json.dumps({"name": "cuc_metacognition_v4_candidate"}),
        )
        archive.writestr(
            "cuc_metacognition_v4_candidate-run_param_id_0_openai_gpt-5.4-2026-03-05.run.json",
            json.dumps(
                _build_v4_run_payload(
                    "CUCV4-PRESERVE-01-SIBLING-STABILITY-LEGAL-CONTRACT"
                )
            ),
        )

    output_dir = tmp_path / "out"
    doc_dir = tmp_path / "docs"
    prefix = "cuc_v4_candidate_2026_04_08_gpt_5_4"
    command = [
        sys.executable,
        "scripts/import_cuc_kaggle_results_zip.py",
        "--zip-path",
        str(zip_path),
        "--output-dir",
        str(output_dir),
        "--doc-dir",
        str(doc_dir),
        "--prefix",
        prefix,
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0

    flat_csv = output_dir / f"cuc_results_flat_{prefix}.csv"
    headline = output_dir / f"{prefix}_headline_metrics.txt"
    summary = output_dir / f"{prefix}_summary.txt"
    findings = doc_dir / f"CUC_findings_{prefix}.md"

    for path in (flat_csv, headline, summary, findings):
        assert path.is_file(), f"Expected generated artifact: {path}"

    with flat_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["model"] == "GPT-5.4"
    assert rows[0]["passed"] == "True"
    assert rows[0]["overall_pass"] == "True"
    assert rows[0]["hard_fail_reasons"] == "[]"
    assert rows[0]["score_story_consistent"] == "True"

    headline_text = headline.read_text(encoding="utf-8")
    summary_text = summary.read_text(encoding="utf-8")
    findings_text = findings.read_text(encoding="utf-8")
    assert "Passed runs: 1/1" in headline_text
    assert "Hard-fail reasons seen: none" in summary_text
    assert "Fabricated-id regressions: none" in findings_text
