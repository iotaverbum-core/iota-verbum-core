from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from import_cuc_kaggle_results_zip import MODEL_COLUMN_KEYS, MODEL_LABELS


REPO_ROOT = Path(__file__).resolve().parents[1]
IMPORT_SCRIPT = REPO_ROOT / "scripts" / "import_cuc_kaggle_results_zip.py"
DEFAULT_SWEEP_ID = "cuc_v4_candidate_2026_04_08"
DEFAULT_DOWNLOADS_ROOT = Path.home() / "Downloads" / DEFAULT_SWEEP_ID
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cuc-results"
DEFAULT_DOC_DIR = REPO_ROOT / "cuc-docs"
DEFAULT_SUMMARY_DOC_NAME = "CUC_V4_CANDIDATE_FIVE_MODEL_SWEEP_2026_04_08.md"
COMPLETED_STATE = "BENCHMARK_TASK_RUN_STATE_COMPLETED"


@dataclass(frozen=True)
class SweepTarget:
    key: str
    folder_name: str
    prefix_suffix: str
    expected_slug: str
    model_label: str


@dataclass(frozen=True)
class SweepJob:
    key: str
    folder_name: str
    prefix: str
    zip_path: Path
    expected_slug: str
    model_label: str
    fallback_used: bool = False
    fallback_for_key: str | None = None


PRIMARY_TARGETS = (
    SweepTarget(
        key="gpt_5_4",
        folder_name="gpt_5_4",
        prefix_suffix="gpt_5_4",
        expected_slug="openai/gpt-5.4-2026-03-05",
        model_label="GPT-5.4",
    ),
    SweepTarget(
        key="claude_sonnet_4_6",
        folder_name="claude_sonnet_4_6",
        prefix_suffix="claude_sonnet_4_6",
        expected_slug="anthropic/claude-sonnet-4-6@default",
        model_label="Claude Sonnet 4.6",
    ),
    SweepTarget(
        key="gemini_2_5_pro",
        folder_name="gemini_2_5_pro",
        prefix_suffix="gemini_2_5_pro",
        expected_slug="google/gemini-2.5-pro",
        model_label="Gemini 2.5 Pro",
    ),
    SweepTarget(
        key="gemini_2_5_flash",
        folder_name="gemini_2_5_flash",
        prefix_suffix="gemini_2_5_flash",
        expected_slug="google/gemini-2.5-flash",
        model_label="Gemini 2.5 Flash",
    ),
)

QWEN_TARGET = SweepTarget(
    key="qwen3_next_80b",
    folder_name="qwen3_next_80b",
    prefix_suffix="qwen3_next_80b",
    expected_slug="qwen/qwen3-next-80b-a3b-thinking",
    model_label="Qwen 3 Next 80B Thinking",
)

DEEPSEEK_FALLBACK_TARGET = SweepTarget(
    key="deepseek_v3_2",
    folder_name="deepseek_v3_2",
    prefix_suffix="deepseek_v3_2",
    expected_slug="deepseek-ai/deepseek-v3.2",
    model_label="DeepSeek V3.2",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the CUC v4 candidate five-model Kaggle sweep and write a combined summary."
    )
    parser.add_argument(
        "--downloads-root",
        type=Path,
        default=DEFAULT_DOWNLOADS_ROOT,
        help="Root directory holding per-model Kaggle result zips.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated CSV and headline metric artifacts.",
    )
    parser.add_argument(
        "--doc-dir",
        type=Path,
        default=DEFAULT_DOC_DIR,
        help="Directory for the combined sweep markdown summary.",
    )
    parser.add_argument(
        "--sweep-id",
        default=DEFAULT_SWEEP_ID,
        help="Prefix used for generated v4 candidate result artifacts.",
    )
    parser.add_argument(
        "--min-models",
        type=int,
        default=4,
        help="Minimum number of successfully imported model zips required for a success exit code.",
    )
    return parser.parse_args()


def resolve_job(
    downloads_root: Path,
    sweep_id: str,
    target: SweepTarget,
    *,
    fallback_used: bool = False,
    fallback_for_key: str | None = None,
) -> SweepJob | None:
    zip_path = downloads_root / target.folder_name / "results.zip"
    if not zip_path.is_file():
        return None
    return SweepJob(
        key=target.key,
        folder_name=target.folder_name,
        prefix=f"{sweep_id}_{target.prefix_suffix}",
        zip_path=zip_path,
        expected_slug=target.expected_slug,
        model_label=target.model_label,
        fallback_used=fallback_used,
        fallback_for_key=fallback_for_key,
    )


def resolve_jobs(downloads_root: Path, sweep_id: str) -> tuple[list[SweepJob], list[str]]:
    jobs: list[SweepJob] = []
    missing: list[str] = []

    for target in PRIMARY_TARGETS:
        job = resolve_job(downloads_root, sweep_id, target)
        if job is None:
            missing.append(target.model_label)
        else:
            jobs.append(job)

    qwen_job = resolve_job(downloads_root, sweep_id, QWEN_TARGET)
    if qwen_job is not None:
        jobs.append(qwen_job)
        return jobs, missing

    deepseek_job = resolve_job(
        downloads_root,
        sweep_id,
        DEEPSEEK_FALLBACK_TARGET,
        fallback_used=True,
        fallback_for_key=QWEN_TARGET.key,
    )
    if deepseek_job is not None:
        jobs.append(deepseek_job)
    else:
        missing.append(f"{QWEN_TARGET.model_label} or {DEEPSEEK_FALLBACK_TARGET.model_label}")
    return jobs, missing


def run_import(job: SweepJob, output_dir: Path, doc_dir: Path) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(IMPORT_SCRIPT),
        "--zip-path",
        str(job.zip_path),
        "--output-dir",
        str(output_dir),
        "--doc-dir",
        str(doc_dir),
        "--prefix",
        job.prefix,
    ]
    return subprocess.run(command, check=False, capture_output=True, text=True)


def read_flat_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_bool(raw: str) -> bool:
    return str(raw).strip().lower() == "true"


def parse_json_list(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def write_model_summary_csv(path: Path, summaries: list[dict[str, object]]) -> None:
    fieldnames = [
        "model",
        "model_slug",
        "zip_path",
        "folder_name",
        "fallback_used",
        "completed_runs",
        "total_runs",
        "passed_runs",
        "pass_rate",
        "task_wiring_errors",
        "score_story_inconsistencies",
        "fabricated_id_regressions",
        "fabricated_evidence_regressions",
        "hard_fail_reasons",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summaries:
            writer.writerow(summary)


def write_case_matrix_csv(
    path: Path,
    case_rows: dict[str, dict[str, dict[str, str]]],
    model_order: list[str],
) -> tuple[int, int, int]:
    fieldnames = ["case_id"]
    for slug in model_order:
        key = MODEL_COLUMN_KEYS.get(slug, slug.replace("/", "_").replace(".", "_"))
        fieldnames.extend(
            [
                f"{key}_passed",
                f"{key}_overall_score",
                f"{key}_hard_fail_reasons",
            ]
        )
    fieldnames.extend(["pass_count", "all_models_passed", "all_models_failed", "has_disagreement"])

    all_pass = 0
    all_fail = 0
    disagreements = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case_id in sorted(case_rows):
            case_out: dict[str, object] = {"case_id": case_id}
            pass_values: list[bool] = []
            for slug in model_order:
                key = MODEL_COLUMN_KEYS.get(slug, slug.replace("/", "_").replace(".", "_"))
                row = case_rows[case_id].get(slug)
                if row is None:
                    case_out[f"{key}_passed"] = ""
                    case_out[f"{key}_overall_score"] = ""
                    case_out[f"{key}_hard_fail_reasons"] = ""
                    continue
                passed = parse_bool(row["passed"])
                pass_values.append(passed)
                case_out[f"{key}_passed"] = row["passed"]
                case_out[f"{key}_overall_score"] = row["overall_score"]
                case_out[f"{key}_hard_fail_reasons"] = row["hard_fail_reasons"]
            case_out["pass_count"] = sum(1 for value in pass_values if value)
            case_out["all_models_passed"] = bool(pass_values) and all(pass_values)
            case_out["all_models_failed"] = bool(pass_values) and not any(pass_values)
            case_out["has_disagreement"] = len(set(pass_values)) > 1 if pass_values else False
            all_pass += int(bool(case_out["all_models_passed"]))
            all_fail += int(bool(case_out["all_models_failed"]))
            disagreements += int(bool(case_out["has_disagreement"]))
            writer.writerow(case_out)

    return all_pass, all_fail, disagreements


def build_doc_name(sweep_id: str) -> str:
    return f"CUC_V4_CANDIDATE_FIVE_MODEL_SWEEP_{sweep_id.rsplit('_', 3)[-3]}_{sweep_id.rsplit('_', 3)[-2]}_{sweep_id.rsplit('_', 3)[-1]}.md"


def build_combined_summary(
    jobs: list[SweepJob],
    rows_by_prefix: dict[str, list[dict[str, str]]],
    import_results: dict[str, subprocess.CompletedProcess[str]],
    missing_models: list[str],
    output_dir: Path,
    doc_dir: Path,
    sweep_id: str,
) -> Path:
    model_summaries: list[dict[str, object]] = []
    case_rows: dict[str, dict[str, dict[str, str]]] = {}
    model_order: list[str] = []

    for job in jobs:
        completed = import_results[job.prefix].returncode == 0
        if not completed:
            continue
        rows = rows_by_prefix[job.prefix]
        if not rows:
            continue
        model_slug = rows[0]["model_slug"]
        model_order.append(model_slug)
        for row in rows:
            case_rows.setdefault(row["case_id"], {})[model_slug] = row

        total_runs = len(rows)
        completed_runs = sum(1 for row in rows if row["state"] == COMPLETED_STATE)
        passed_runs = sum(1 for row in rows if parse_bool(row["passed"]))
        task_wiring_errors = sum(1 for row in rows if row["state"] != COMPLETED_STATE)
        score_story_inconsistencies = sum(
            1 for row in rows if not parse_bool(row["score_story_consistent"])
        )
        fabricated_id_regressions = sum(
            1 for row in rows if parse_bool(row["fabricated_ids_hard_fail"])
        )
        fabricated_evidence_regressions = sum(
            1 for row in rows if parse_bool(row["fabricated_evidence_ids_hard_fail"])
        )
        hard_fail_reasons = sorted(
            {
                reason
                for row in rows
                for reason in parse_json_list(row["hard_fail_reasons"])
            }
        )
        model_summaries.append(
            {
                "model": rows[0]["model"],
                "model_slug": model_slug,
                "zip_path": str(job.zip_path),
                "folder_name": job.folder_name,
                "fallback_used": job.fallback_used,
                "completed_runs": completed_runs,
                "total_runs": total_runs,
                "passed_runs": passed_runs,
                "pass_rate": f"{(passed_runs / total_runs) * 100:.1f}%" if total_runs else "0.0%",
                "task_wiring_errors": task_wiring_errors,
                "score_story_inconsistencies": score_story_inconsistencies,
                "fabricated_id_regressions": fabricated_id_regressions,
                "fabricated_evidence_regressions": fabricated_evidence_regressions,
                "hard_fail_reasons": ", ".join(hard_fail_reasons) if hard_fail_reasons else "none",
            }
        )

    model_summary_csv = output_dir / f"{sweep_id}_model_summary.csv"
    write_model_summary_csv(model_summary_csv, model_summaries)

    case_matrix_csv = output_dir / f"{sweep_id}_case_matrix.csv"
    all_pass_cases, all_fail_cases, disagreement_cases = write_case_matrix_csv(
        case_matrix_csv, case_rows, model_order
    )

    fabricated_ids_reappeared = any(
        int(summary["fabricated_id_regressions"]) > 0 for summary in model_summaries
    )
    fabricated_evidence_reappeared = any(
        int(summary["fabricated_evidence_regressions"]) > 0 for summary in model_summaries
    )
    score_story_consistent = all(
        int(summary["score_story_inconsistencies"]) == 0 for summary in model_summaries
    )

    if disagreement_cases == 0:
        separation_read = "mostly ties"
    elif disagreement_cases == len(case_rows):
        separation_read = "meaningful separation across every imported candidate case"
    else:
        separation_read = f"partial separation ({disagreement_cases}/{len(case_rows)} cases show disagreement)"

    doc_path = doc_dir / build_doc_name(sweep_id)
    lines = [
        "# CUC v4 Candidate Five-Model Sweep",
        "",
        "## Completed runs vs errors",
        f"- Imported model zips: {len(model_summaries)}/{len(jobs) + len(missing_models)} expected sweep slots",
        f"- Missing model slots: {', '.join(missing_models) if missing_models else 'none'}",
    ]
    fallback_jobs = [job for job in jobs if job.fallback_used]
    if fallback_jobs:
        lines.append(
            f"- Fallback used: {fallback_jobs[0].model_label} replaced the {QWEN_TARGET.model_label} slot"
        )
    else:
        lines.append("- Fallback used: none")

    import_failures = [
        job.model_label
        for job in jobs
        if import_results[job.prefix].returncode != 0
    ]
    lines.append(
        f"- Import errors: {', '.join(import_failures) if import_failures else 'none'}"
    )
    lines.extend(["", "## Per-model pass count on the 2-case pack"])
    for summary in model_summaries:
        lines.append(
            f"- {summary['model']}: {summary['passed_runs']}/{summary['total_runs']} "
            f"(task-wiring errors={summary['task_wiring_errors']}, score/export inconsistencies={summary['score_story_inconsistencies']})"
        )

    lines.extend(["", "## Hard fail reasons"])
    for summary in model_summaries:
        lines.append(f"- {summary['model']}: {summary['hard_fail_reasons']}")

    lines.extend(
        [
            "",
            "## Fabricated-id regression check",
            f"- fabricated_ids reappeared: {'yes' if fabricated_ids_reappeared else 'no'}",
            f"- fabricated_evidence_ids reappeared: {'yes' if fabricated_evidence_reappeared else 'no'}",
            "",
            "## Scorer/export consistency",
            f"- overall_pass remained consistent with imported Kaggle results: {'yes' if score_story_consistent else 'no'}",
            "",
            "## Separation read",
            f"- All-pass cases: {all_pass_cases}/{len(case_rows)}",
            f"- All-fail cases: {all_fail_cases}/{len(case_rows)}",
            f"- Disagreement cases: {disagreement_cases}/{len(case_rows)}",
            f"- Assessment: {separation_read}",
            "",
            "## Recommendation",
            "- Expand to 24+ cases before spending more model budget. This 2-case sweep is useful for smoke-comparison and regression checking, but not for flagship leaderboard claims.",
            "",
            "## Generated artifacts",
            f"- [model summary csv]({model_summary_csv.as_posix()})",
            f"- [case matrix csv]({case_matrix_csv.as_posix()})",
        ]
    )
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return doc_path


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.doc_dir.mkdir(parents=True, exist_ok=True)

    jobs, missing_models = resolve_jobs(args.downloads_root, args.sweep_id)
    if not jobs:
        raise RuntimeError(f"No result zips found under {args.downloads_root}")

    rows_by_prefix: dict[str, list[dict[str, str]]] = {}
    import_results: dict[str, subprocess.CompletedProcess[str]] = {}
    for job in jobs:
        completed = run_import(job, args.output_dir, args.doc_dir)
        import_results[job.prefix] = completed
        if completed.returncode != 0:
            continue
        flat_csv = args.output_dir / f"cuc_results_flat_{job.prefix}.csv"
        rows_by_prefix[job.prefix] = read_flat_rows(flat_csv)

    doc_path = build_combined_summary(
        jobs,
        rows_by_prefix,
        import_results,
        missing_models,
        args.output_dir,
        args.doc_dir,
        args.sweep_id,
    )

    for job in jobs:
        completed = import_results[job.prefix]
        status = "ok" if completed.returncode == 0 else "error"
        print(f"{job.model_label}: {status} ({job.zip_path})")
        if completed.returncode != 0 and completed.stderr:
            print(completed.stderr.strip())
    print(f"Wrote {doc_path}")

    successful_models = sum(1 for result in import_results.values() if result.returncode == 0)
    if successful_models < args.min_models:
        raise SystemExit(
            f"Imported only {successful_models} model zips; expected at least {args.min_models}."
        )


if __name__ == "__main__":
    main()
