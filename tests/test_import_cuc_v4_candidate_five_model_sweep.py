from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


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
    model_slug: str,
    overall_pass: bool,
    overall_score: float,
    hard_fail_reasons: list[str] | None = None,
) -> dict[str, object]:
    hard_fail_reasons = hard_fail_reasons or []
    score = {
        "hard_fail_reasons": hard_fail_reasons,
        "axis_scores": {
            "delta_detection": 1.0,
            "causal_temporal_propagation": 0.8 if overall_pass else 0.4,
            "selective_revision": 1.0,
            "unknown_ledger_discipline": 1.0,
            "evidence_grounding": 1.0,
        },
        "overall_score": overall_score,
        "overall_pass": overall_pass,
    }
    assertions = [
        _v4_assertion(
            expectation=(
                f"{case_id} should avoid hard fails around changed artifact Artifact-X: "
                f"{hard_fail_reasons}"
            ),
            passed=not hard_fail_reasons,
        ),
        _v4_assertion(
            expectation=(
                f"{case_id} should detect the revised branch ['state:x']. "
                f"axis_scores={score['axis_scores']}"
            ),
            passed=True,
        ),
        _v4_assertion(
            expectation=(
                f"{case_id} should ground its revisions in Artifact-X. "
                f"axis_scores={score['axis_scores']}"
            ),
            passed=True,
        ),
        _v4_assertion(
            expectation=(
                f"{case_id} should preserve stable sibling claims ['state:y'] while revising "
                f"only impacted claims. axis_scores={score['axis_scores']}"
            ),
            passed=True,
        ),
        _v4_assertion(
            expectation=(
                f"{case_id} should propagate the revision through dependent claims. "
                f"causal_chain={{'chain': ['C1']}} axis_scores={score['axis_scores']}"
            ),
            passed=overall_pass,
        ),
        _v4_assertion(
            expectation=(
                f"{case_id} should satisfy the v4 candidate structured pass rule. "
                f"family_id=test render_profile=test hop_depth=2 "
                f"named_evidence_artifact=Artifact-X score={score}"
            ),
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


def _write_results_zip(
    root: Path,
    folder_name: str,
    model_slug: str,
    case_outcomes: list[tuple[str, bool, float]],
) -> Path:
    folder = root / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    zip_path = folder / "results.zip"
    with ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "cuc_metacognition_v4_candidate.task.json",
            json.dumps({"name": "cuc_metacognition_v4_candidate"}),
        )
        for param_id, (case_id, overall_pass, overall_score) in enumerate(case_outcomes):
            file_slug = (
                model_slug.replace("/", "_")
                .replace("@", "_")
                .replace(".", "_")
                .replace("-", "_")
            )
            archive.writestr(
                f"cuc_metacognition_v4_candidate-run_param_id_{param_id}_{file_slug}.run.json",
                json.dumps(
                    _build_v4_run_payload(
                        case_id,
                        model_slug=model_slug,
                        overall_pass=overall_pass,
                        overall_score=overall_score,
                    )
                ),
            )
    return zip_path


def test_import_cuc_v4_candidate_five_model_sweep_builds_combined_summary(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    downloads_root = tmp_path / "downloads"
    output_dir = tmp_path / "out"
    doc_dir = tmp_path / "docs"
    sweep_id = "cuc_v4_candidate_2026_04_08"

    case_outcomes = {
        "gpt_5_4": [
            ("CUCV4-PRESERVE-01", True, 0.90),
            ("CUCV4-PRESERVE-02", True, 0.88),
        ],
        "claude_sonnet_4_6": [
            ("CUCV4-PRESERVE-01", True, 0.89),
            ("CUCV4-PRESERVE-02", False, 0.61),
        ],
        "gemini_2_5_pro": [
            ("CUCV4-PRESERVE-01", True, 0.91),
            ("CUCV4-PRESERVE-02", False, 0.58),
        ],
        "gemini_2_5_flash": [
            ("CUCV4-PRESERVE-01", True, 0.87),
            ("CUCV4-PRESERVE-02", True, 0.82),
        ],
        "qwen3_next_80b": [
            ("CUCV4-PRESERVE-01", True, 0.85),
            ("CUCV4-PRESERVE-02", False, 0.55),
        ],
    }
    _write_results_zip(
        downloads_root,
        "gpt_5_4",
        "openai/gpt-5.4-2026-03-05",
        case_outcomes["gpt_5_4"],
    )
    _write_results_zip(
        downloads_root,
        "claude_sonnet_4_6",
        "anthropic/claude-sonnet-4-6@default",
        case_outcomes["claude_sonnet_4_6"],
    )
    _write_results_zip(
        downloads_root,
        "gemini_2_5_pro",
        "google/gemini-2.5-pro",
        case_outcomes["gemini_2_5_pro"],
    )
    _write_results_zip(
        downloads_root,
        "gemini_2_5_flash",
        "google/gemini-2.5-flash",
        case_outcomes["gemini_2_5_flash"],
    )
    _write_results_zip(
        downloads_root,
        "qwen3_next_80b",
        "qwen/qwen3-next-80b-a3b-thinking",
        case_outcomes["qwen3_next_80b"],
    )

    command = [
        sys.executable,
        "scripts/import_cuc_v4_candidate_five_model_sweep.py",
        "--downloads-root",
        str(downloads_root),
        "--output-dir",
        str(output_dir),
        "--doc-dir",
        str(doc_dir),
        "--sweep-id",
        sweep_id,
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr

    model_summary_csv = output_dir / f"{sweep_id}_model_summary.csv"
    case_matrix_csv = output_dir / f"{sweep_id}_case_matrix.csv"
    summary_doc = doc_dir / "CUC_V4_CANDIDATE_FIVE_MODEL_SWEEP_2026_04_08.md"
    for path in (model_summary_csv, case_matrix_csv, summary_doc):
        assert path.is_file(), f"Expected generated artifact: {path}"

    with model_summary_csv.open(encoding="utf-8", newline="") as handle:
        model_rows = list(csv.DictReader(handle))
    assert len(model_rows) == 5
    assert {row["model"] for row in model_rows} == {
        "GPT-5.4",
        "Claude Sonnet 4.6",
        "Gemini 2.5 Pro",
        "Gemini 2.5 Flash",
        "Qwen 3 Next 80B Thinking",
    }

    with case_matrix_csv.open(encoding="utf-8", newline="") as handle:
        case_rows = {row["case_id"]: row for row in csv.DictReader(handle)}
    assert set(case_rows) == {"CUCV4-PRESERVE-01", "CUCV4-PRESERVE-02"}
    assert case_rows["CUCV4-PRESERVE-01"]["all_models_passed"] == "True"
    assert case_rows["CUCV4-PRESERVE-02"]["has_disagreement"] == "True"

    summary_text = summary_doc.read_text(encoding="utf-8")
    assert "Imported model zips: 5/5 expected sweep slots" in summary_text
    assert "Fallback used: none" in summary_text
    assert "fabricated_ids reappeared: no" in summary_text
    assert "fabricated_evidence_ids reappeared: no" in summary_text
    assert "overall_pass remained consistent with imported Kaggle results: yes" in summary_text
    assert "Assessment: partial separation (1/2 cases show disagreement)" in summary_text
    assert "Expand to 24+ cases before spending more model budget." in summary_text


def test_import_cuc_v4_candidate_five_model_sweep_uses_deepseek_fallback(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    downloads_root = tmp_path / "downloads"
    output_dir = tmp_path / "out"
    doc_dir = tmp_path / "docs"
    sweep_id = "cuc_v4_candidate_2026_04_08"

    shared_cases = [
        ("CUCV4-PRESERVE-01", True, 0.90),
        ("CUCV4-PRESERVE-02", True, 0.83),
    ]
    _write_results_zip(
        downloads_root,
        "gpt_5_4",
        "openai/gpt-5.4-2026-03-05",
        shared_cases,
    )
    _write_results_zip(
        downloads_root,
        "claude_sonnet_4_6",
        "anthropic/claude-sonnet-4-6@default",
        shared_cases,
    )
    _write_results_zip(
        downloads_root,
        "gemini_2_5_pro",
        "google/gemini-2.5-pro",
        shared_cases,
    )
    _write_results_zip(
        downloads_root,
        "gemini_2_5_flash",
        "google/gemini-2.5-flash",
        shared_cases,
    )
    _write_results_zip(
        downloads_root,
        "deepseek_v3_2",
        "deepseek-ai/deepseek-v3.2",
        shared_cases,
    )

    command = [
        sys.executable,
        "scripts/import_cuc_v4_candidate_five_model_sweep.py",
        "--downloads-root",
        str(downloads_root),
        "--output-dir",
        str(output_dir),
        "--doc-dir",
        str(doc_dir),
        "--sweep-id",
        sweep_id,
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr

    model_summary_csv = output_dir / f"{sweep_id}_model_summary.csv"
    summary_doc = doc_dir / "CUC_V4_CANDIDATE_FIVE_MODEL_SWEEP_2026_04_08.md"
    assert model_summary_csv.is_file()
    assert summary_doc.is_file()

    with model_summary_csv.open(encoding="utf-8", newline="") as handle:
        model_rows = list(csv.DictReader(handle))
    assert {row["model"] for row in model_rows} == {
        "GPT-5.4",
        "Claude Sonnet 4.6",
        "Gemini 2.5 Pro",
        "Gemini 2.5 Flash",
        "DeepSeek V3.2",
    }

    summary_text = summary_doc.read_text(encoding="utf-8")
    assert "Imported model zips: 5/5 expected sweep slots" in summary_text
    assert (
        "Fallback used: DeepSeek V3.2 replaced the Qwen 3 Next 80B Thinking slot"
        in summary_text
    )
    assert "Missing model slots: none" in summary_text


def test_import_cuc_v4_candidate_five_model_sweep_requires_four_models(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    downloads_root = tmp_path / "downloads"
    output_dir = tmp_path / "out"
    doc_dir = tmp_path / "docs"

    shared_cases = [
        ("CUCV4-PRESERVE-01", True, 0.90),
        ("CUCV4-PRESERVE-02", True, 0.83),
    ]
    _write_results_zip(
        downloads_root,
        "gpt_5_4",
        "openai/gpt-5.4-2026-03-05",
        shared_cases,
    )
    _write_results_zip(
        downloads_root,
        "claude_sonnet_4_6",
        "anthropic/claude-sonnet-4-6@default",
        shared_cases,
    )
    _write_results_zip(
        downloads_root,
        "gemini_2_5_pro",
        "google/gemini-2.5-pro",
        shared_cases,
    )

    command = [
        sys.executable,
        "scripts/import_cuc_v4_candidate_five_model_sweep.py",
        "--downloads-root",
        str(downloads_root),
        "--output-dir",
        str(output_dir),
        "--doc-dir",
        str(doc_dir),
        "--sweep-id",
        "cuc_v4_candidate_2026_04_08",
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "Imported only 3 model zips; expected at least 4." in (
        completed.stderr + completed.stdout
    )
