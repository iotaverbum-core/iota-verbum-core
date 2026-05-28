"""Import Kaggle benchmark results into repo-side CUC result artifacts."""

from __future__ import annotations

import ast
import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile


MODEL_LABELS = {
    "anthropic/claude-sonnet-4-6@default": "Claude Sonnet 4.6",
    "anthropic/claude-sonnet-4-5@20250929": "Claude Sonnet 4.5",
    "deepseek-ai/deepseek-v3.2": "DeepSeek V3.2",
    "deepseek-ai/deepseek-v3.1": "DeepSeek V3.1",
    "google/gemini-2.5-pro": "Gemini 2.5 Pro",
    "google/gemini-2.5-flash": "Gemini 2.5 Flash",
    "openai/gpt-5.4-2026-03-05": "GPT-5.4",
    "qwen/qwen3-next-80b-a3b-thinking": "Qwen 3 Next 80B Thinking",
}

MODEL_COLUMN_KEYS = {
    "anthropic/claude-sonnet-4-6@default": "claude_sonnet_4_6",
    "anthropic/claude-sonnet-4-5@20250929": "claude_sonnet_4_5",
    "deepseek-ai/deepseek-v3.2": "deepseek_v3_2",
    "deepseek-ai/deepseek-v3.1": "deepseek_v3_1",
    "google/gemini-2.5-pro": "gemini_2_5_pro",
    "google/gemini-2.5-flash": "gemini_2_5_flash",
    "openai/gpt-5.4-2026-03-05": "gpt_5_4",
    "qwen/qwen3-next-80b-a3b-thinking": "qwen3_next_80b_a3b_thinking",
}

PARAM_ID_RE = re.compile(r"run_param_id_(\d+)")
PASSED_SUFFIX = "PASSED"
ONE_JUDGE_EXPECTATION = "should return one judge result per criterion"
OVERALL_PASS_EXPECTATION = "should pass at least 11 of 15 criteria"
CRITERION_TOKEN = "criterion "


@dataclass(frozen=True)
class RunRow:
    case_id: str
    model_slug: str
    model_label: str
    passed: bool
    strict_clean_pass: bool
    clean_run: bool
    one_judge_per_criterion_ok: bool
    overall_threshold_assertion_ok: bool
    criteria_passed: int
    criteria_total: int
    duration_seconds: float
    start_time: str
    end_time: str
    state: str
    param_id: int
    file_name: str


@dataclass(frozen=True)
class V4CandidateRunRow:
    case_id: str
    model_slug: str
    model_label: str
    passed: bool
    state: str
    overall_pass: bool
    overall_score: float
    hard_fail_reasons: tuple[str, ...]
    fabricated_ids_hard_fail: bool
    fabricated_evidence_ids_hard_fail: bool
    score_story_consistent: bool
    assertion_fail_count: int
    axis_delta_detection: float
    axis_causal_temporal_propagation: float
    axis_selective_revision: float
    axis_unknown_ledger_discipline: float
    axis_evidence_grounding: float
    duration_seconds: float
    start_time: str
    end_time: str
    param_id: int
    file_name: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Kaggle benchmark results from a zip or results directory."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--zip-path", type=Path, help="Results zip to import.")
    source_group.add_argument(
        "--results-dir",
        type=Path,
        help="Directory containing the hosted .task.json and .run.json files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("cuc-results"),
        help="Output directory for text and CSV artifacts.",
    )
    parser.add_argument(
        "--doc-dir",
        type=Path,
        default=Path("cuc-docs"),
        help="Output directory for findings markdown.",
    )
    parser.add_argument(
        "--prefix",
        default="cuc_legal_v2",
        help="Prefix for generated artifact filenames.",
    )
    return parser.parse_args()


def status_is_passed(status: str) -> bool:
    return status.endswith(PASSED_SUFFIX)


def parse_timestamp(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def parse_param_id(file_name: str) -> int:
    match = PARAM_ID_RE.search(file_name)
    if match is None:
        raise ValueError(f"Could not parse param id from {file_name}")
    return int(match.group(1))


def parse_case_id(assertions: list[dict[str, object]]) -> str:
    if not assertions:
        raise ValueError("Run payload has no assertions to recover case_id from.")
    expectation = str(assertions[0]["expectation"])
    case_id, _, _ = expectation.partition(" should ")
    if not case_id:
        raise ValueError(f"Could not parse case_id from expectation: {expectation}")
    return case_id


def build_run_rows(run_payloads: list[tuple[str, dict[str, object]]]) -> list[RunRow]:
    rows: list[RunRow] = []
    for file_name, payload in sorted(run_payloads, key=lambda item: item[0]):
        model_slug = str(payload["modelVersion"]["slug"])
        model_label = MODEL_LABELS.get(model_slug, model_slug)
        assertions = list(payload.get("assertions", []))
        case_id = parse_case_id(assertions)
        results = list(payload.get("results", []))
        passed = bool(results[0].get("booleanResult")) if results else False
        one_judge_ok = any(
            ONE_JUDGE_EXPECTATION in str(assertion["expectation"])
            and status_is_passed(str(assertion["status"]))
            for assertion in assertions
        )
        overall_threshold_assertion_ok = any(
            OVERALL_PASS_EXPECTATION in str(assertion["expectation"])
            and status_is_passed(str(assertion["status"]))
            for assertion in assertions
        )
        criteria_assertions = [
            assertion
            for assertion in assertions
            if CRITERION_TOKEN in str(assertion["expectation"])
        ]
        criteria_total = len(criteria_assertions)
        criteria_passed = sum(
            1 for assertion in criteria_assertions if status_is_passed(str(assertion["status"]))
        )
        clean_run = one_judge_ok and criteria_total == 15
        strict_clean_pass = passed and clean_run
        start_time = str(payload["startTime"])
        end_time = str(payload["endTime"])
        duration_seconds = (
            parse_timestamp(end_time) - parse_timestamp(start_time)
        ).total_seconds()
        rows.append(
            RunRow(
                case_id=case_id,
                model_slug=model_slug,
                model_label=model_label,
                passed=passed,
                strict_clean_pass=strict_clean_pass,
                clean_run=clean_run,
                one_judge_per_criterion_ok=one_judge_ok,
                overall_threshold_assertion_ok=overall_threshold_assertion_ok,
                criteria_passed=criteria_passed,
                criteria_total=criteria_total,
                duration_seconds=duration_seconds,
                start_time=start_time,
                end_time=end_time,
                state=str(payload.get("state", "")),
                param_id=parse_param_id(file_name),
                file_name=file_name,
            )
        )
    return rows


def safe_literal_eval(raw: str) -> object | None:
    try:
        return ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return None


def parse_v4_hard_fail_reasons(assertions: list[dict[str, object]]) -> list[str]:
    marker = " should avoid hard fails around changed artifact "
    for assertion in assertions:
        expectation = str(assertion.get("expectation", ""))
        if marker not in expectation:
            continue
        if ":" not in expectation:
            continue
        raw_reasons = expectation.rsplit(":", 1)[1].strip()
        parsed = safe_literal_eval(raw_reasons)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def parse_v4_score(assertions: list[dict[str, object]]) -> dict[str, object]:
    marker = " score="
    for assertion in assertions:
        expectation = str(assertion.get("expectation", ""))
        if marker not in expectation:
            continue
        raw_score = expectation.split(marker, 1)[1].strip()
        parsed = safe_literal_eval(raw_score)
        if isinstance(parsed, dict):
            return parsed
    return {}


def build_v4_candidate_run_rows(
    run_payloads: list[tuple[str, dict[str, object]]],
) -> list[V4CandidateRunRow]:
    rows: list[V4CandidateRunRow] = []
    for file_name, payload in sorted(run_payloads, key=lambda item: item[0]):
        model_slug = str(payload["modelVersion"]["slug"])
        model_label = MODEL_LABELS.get(model_slug, model_slug)
        assertions = list(payload.get("assertions", []))
        case_id = parse_case_id(assertions)
        results = list(payload.get("results", []))
        passed = bool(results[0].get("booleanResult")) if results else False
        hard_fail_reasons = tuple(parse_v4_hard_fail_reasons(assertions))
        score = parse_v4_score(assertions)
        axis_scores = score.get("axis_scores", {}) if isinstance(score, dict) else {}
        overall_pass = bool(score.get("overall_pass", passed)) if isinstance(score, dict) else passed
        overall_score = float(score.get("overall_score", 0.0)) if isinstance(score, dict) else 0.0
        start_time = str(payload["startTime"])
        end_time = str(payload["endTime"])
        assertion_fail_count = sum(
            1
            for assertion in assertions
            if not status_is_passed(str(assertion.get("status", "")))
        )
        rows.append(
            V4CandidateRunRow(
                case_id=case_id,
                model_slug=model_slug,
                model_label=model_label,
                passed=passed,
                state=str(payload.get("state", "")),
                overall_pass=overall_pass,
                overall_score=overall_score,
                hard_fail_reasons=hard_fail_reasons,
                fabricated_ids_hard_fail="fabricated_ids" in hard_fail_reasons,
                fabricated_evidence_ids_hard_fail="fabricated_evidence_ids" in hard_fail_reasons,
                score_story_consistent=passed == overall_pass,
                assertion_fail_count=assertion_fail_count,
                axis_delta_detection=float(axis_scores.get("delta_detection", 0.0)),
                axis_causal_temporal_propagation=float(
                    axis_scores.get("causal_temporal_propagation", 0.0)
                ),
                axis_selective_revision=float(axis_scores.get("selective_revision", 0.0)),
                axis_unknown_ledger_discipline=float(
                    axis_scores.get("unknown_ledger_discipline", 0.0)
                ),
                axis_evidence_grounding=float(axis_scores.get("evidence_grounding", 0.0)),
                duration_seconds=(
                    parse_timestamp(end_time) - parse_timestamp(start_time)
                ).total_seconds(),
                start_time=start_time,
                end_time=end_time,
                param_id=parse_param_id(file_name),
                file_name=file_name,
            )
        )
    return rows


def load_run_rows_from_zip(zip_path: Path) -> tuple[str, list[RunRow]]:
    if not zip_path.is_file():
        raise FileNotFoundError(f"Results zip not found: {zip_path}")

    task_name = "unknown_task"
    run_payloads: list[tuple[str, dict[str, object]]] = []
    with ZipFile(zip_path) as archive:
        task_files = [name for name in archive.namelist() if name.endswith(".task.json")]
        if task_files:
            task_payload = json.loads(archive.read(task_files[0]))
            task_name = str(task_payload.get("name", task_name))

        for file_name in sorted(name for name in archive.namelist() if name.endswith(".run.json")):
            run_payloads.append((file_name, json.loads(archive.read(file_name))))
    return task_name, build_run_rows(run_payloads)


def load_run_rows_from_dir(results_dir: Path) -> tuple[str, list[RunRow]]:
    if not results_dir.is_dir():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    task_name = "unknown_task"
    task_files = sorted(results_dir.glob("*.task.json"))
    if task_files:
        task_payload = json.loads(task_files[0].read_text(encoding="utf-8"))
        task_name = str(task_payload.get("name", task_name))

    run_payloads = [
        (path.name, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(results_dir.glob("*.run.json"))
    ]
    return task_name, build_run_rows(run_payloads)


def load_run_rows(
    *, zip_path: Path | None = None, results_dir: Path | None = None
) -> tuple[str, list[RunRow]]:
    if (zip_path is None) == (results_dir is None):
        raise ValueError("Provide exactly one of --zip-path or --results-dir.")
    if zip_path is not None:
        return load_run_rows_from_zip(zip_path)
    assert results_dir is not None
    return load_run_rows_from_dir(results_dir)


def load_v4_candidate_run_rows_from_zip(
    zip_path: Path,
) -> tuple[str, list[V4CandidateRunRow]]:
    if not zip_path.is_file():
        raise FileNotFoundError(f"Results zip not found: {zip_path}")

    task_name = "unknown_task"
    run_payloads: list[tuple[str, dict[str, object]]] = []
    with ZipFile(zip_path) as archive:
        task_files = [name for name in archive.namelist() if name.endswith(".task.json")]
        if task_files:
            task_payload = json.loads(archive.read(task_files[0]))
            task_name = str(task_payload.get("name", task_name))

        for file_name in sorted(name for name in archive.namelist() if name.endswith(".run.json")):
            run_payload = json.loads(archive.read(file_name))
            task_name = str(
                run_payload.get("taskVersion", {}).get("name", task_name)
            )
            run_payloads.append((file_name, run_payload))
    return task_name, build_v4_candidate_run_rows(run_payloads)


def load_v4_candidate_run_rows_from_dir(
    results_dir: Path,
) -> tuple[str, list[V4CandidateRunRow]]:
    if not results_dir.is_dir():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    task_name = "unknown_task"
    task_files = sorted(results_dir.glob("*.task.json"))
    if task_files:
        task_payload = json.loads(task_files[0].read_text(encoding="utf-8"))
        task_name = str(task_payload.get("name", task_name))

    run_payloads: list[tuple[str, dict[str, object]]] = []
    for path in sorted(results_dir.glob("*.run.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        task_name = str(payload.get("taskVersion", {}).get("name", task_name))
        run_payloads.append((path.name, payload))
    return task_name, build_v4_candidate_run_rows(run_payloads)


def load_v4_candidate_run_rows(
    *, zip_path: Path | None = None, results_dir: Path | None = None
) -> tuple[str, list[V4CandidateRunRow]]:
    if (zip_path is None) == (results_dir is None):
        raise ValueError("Provide exactly one of --zip-path or --results-dir.")
    if zip_path is not None:
        return load_v4_candidate_run_rows_from_zip(zip_path)
    assert results_dir is not None
    return load_v4_candidate_run_rows_from_dir(results_dir)


def format_pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def write_flat_csv(path: Path, rows: list[RunRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model",
        "model_slug",
        "case_id",
        "passed",
        "strict_clean_pass",
        "clean_run",
        "one_judge_per_criterion_ok",
        "overall_threshold_assertion_ok",
        "criteria_passed",
        "criteria_total",
        "duration_seconds",
        "start_time",
        "end_time",
        "state",
        "param_id",
        "file",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (item.model_label, item.param_id, item.case_id)):
            writer.writerow(
                {
                    "model": row.model_label,
                    "model_slug": row.model_slug,
                    "case_id": row.case_id,
                    "passed": row.passed,
                    "strict_clean_pass": row.strict_clean_pass,
                    "clean_run": row.clean_run,
                    "one_judge_per_criterion_ok": row.one_judge_per_criterion_ok,
                    "overall_threshold_assertion_ok": row.overall_threshold_assertion_ok,
                    "criteria_passed": row.criteria_passed,
                    "criteria_total": row.criteria_total,
                    "duration_seconds": f"{row.duration_seconds:.3f}",
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "state": row.state,
                    "param_id": row.param_id,
                    "file": row.file_name,
                }
            )


def write_case_matrix(path: Path, rows: list[RunRow]) -> tuple[int, int, int]:
    by_case: dict[str, dict[str, RunRow]] = defaultdict(dict)
    for row in rows:
        by_case[row.case_id][row.model_slug] = row

    ordered_model_slugs = sorted(
        {row.model_slug for row in rows},
        key=lambda slug: MODEL_LABELS.get(slug, slug),
    )

    fieldnames = ["case_id"]
    for slug in ordered_model_slugs:
        key = MODEL_COLUMN_KEYS.get(slug, slug.replace("/", "_").replace(".", "_"))
        fieldnames.extend(
            [
                f"{key}_passed",
                f"{key}_strict_clean_pass",
                f"{key}_criteria_passed",
                f"{key}_criteria_total",
            ]
        )
    fieldnames.extend(["pass_count", "strict_clean_pass_count", "all_models_passed", "all_models_failed", "has_disagreement"])

    all_pass = 0
    all_fail = 0
    disagreements = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case_id in sorted(by_case):
            case_rows = by_case[case_id]
            pass_values = [case_rows[slug].passed for slug in ordered_model_slugs]
            strict_pass_values = [case_rows[slug].strict_clean_pass for slug in ordered_model_slugs]
            row_out: dict[str, object] = {"case_id": case_id}
            for slug in ordered_model_slugs:
                key = MODEL_COLUMN_KEYS.get(slug, slug.replace("/", "_").replace(".", "_"))
                run_row = case_rows[slug]
                row_out[f"{key}_passed"] = run_row.passed
                row_out[f"{key}_strict_clean_pass"] = run_row.strict_clean_pass
                row_out[f"{key}_criteria_passed"] = run_row.criteria_passed
                row_out[f"{key}_criteria_total"] = run_row.criteria_total
            row_out["pass_count"] = sum(1 for value in pass_values if value)
            row_out["strict_clean_pass_count"] = sum(1 for value in strict_pass_values if value)
            row_out["all_models_passed"] = all(pass_values)
            row_out["all_models_failed"] = not any(pass_values)
            row_out["has_disagreement"] = len(set(pass_values)) > 1
            all_pass += int(bool(row_out["all_models_passed"]))
            all_fail += int(bool(row_out["all_models_failed"]))
            disagreements += int(bool(row_out["has_disagreement"]))
            writer.writerow(row_out)

    return all_pass, all_fail, disagreements


def build_per_model_stats(rows: list[RunRow]) -> list[dict[str, object]]:
    by_model: dict[str, list[RunRow]] = defaultdict(list)
    for row in rows:
        by_model[row.model_slug].append(row)

    stats: list[dict[str, object]] = []
    for model_slug, model_rows in by_model.items():
        case_count = len(model_rows)
        boolean_passes = sum(1 for row in model_rows if row.passed)
        strict_clean_passes = sum(1 for row in model_rows if row.strict_clean_pass)
        clean_runs = sum(1 for row in model_rows if row.clean_run)
        total_seconds = sum(row.duration_seconds for row in model_rows)
        failed_cases = sorted(
            (row for row in model_rows if not row.passed),
            key=lambda item: item.case_id,
        )
        malformed_cases = sorted(
            (row for row in model_rows if not row.clean_run),
            key=lambda item: item.case_id,
        )
        stats.append(
            {
                "model_slug": model_slug,
                "model_label": MODEL_LABELS.get(model_slug, model_slug),
                "case_count": case_count,
                "boolean_passes": boolean_passes,
                "strict_clean_passes": strict_clean_passes,
                "clean_runs": clean_runs,
                "total_seconds": total_seconds,
                "avg_seconds": total_seconds / case_count if case_count else 0.0,
                "failed_cases": failed_cases,
                "malformed_cases": malformed_cases,
            }
        )
    stats.sort(key=lambda item: (-int(item["boolean_passes"]), str(item["model_label"])))
    return stats


def write_headline_metrics(
    path: Path,
    task_name: str,
    source_name: str,
    rows: list[RunRow],
    per_model_stats: list[dict[str, object]],
    all_pass_cases: int,
    all_fail_cases: int,
    disagreement_cases: int,
) -> None:
    total_runs = len(rows)
    completed_runs = sum(1 for row in rows if row.state == "BENCHMARK_TASK_RUN_STATE_COMPLETED")
    boolean_passes = sum(1 for row in rows if row.passed)
    strict_clean_passes = sum(1 for row in rows if row.strict_clean_pass)
    lines = [
        f"{task_name} hosted 50-case results ({source_name})",
        f"- Completed runs: {completed_runs}/{total_runs}",
        f"- Boolean passes: {boolean_passes}/{total_runs} = {format_pct(boolean_passes, total_runs)}",
        f"- Strict-clean passes: {strict_clean_passes}/{total_runs} = {format_pct(strict_clean_passes, total_runs)}",
        f"- All-pass cases: {all_pass_cases}/50",
        f"- All-fail cases: {all_fail_cases}/50",
        f"- Disagreement cases: {disagreement_cases}/50",
        "- Per-model boolean case pass:",
    ]
    for stat in per_model_stats:
        lines.append(
            f"  - {stat['model_label']}: {stat['boolean_passes']}/{stat['case_count']} = "
            f"{format_pct(int(stat['boolean_passes']), int(stat['case_count']))}"
        )
    lines.append("- Per-model strict-clean case pass:")
    for stat in per_model_stats:
        lines.append(
            f"  - {stat['model_label']}: {stat['strict_clean_passes']}/{stat['case_count']} = "
            f"{format_pct(int(stat['strict_clean_passes']), int(stat['case_count']))} "
            f"({stat['clean_runs']}/{stat['case_count']} clean runs)"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    path: Path,
    task_name: str,
    source_name: str,
    rows: list[RunRow],
    per_model_stats: list[dict[str, object]],
    all_pass_cases: int,
    all_fail_cases: int,
    disagreement_cases: int,
) -> None:
    total_runs = len(rows)
    completed_runs = sum(1 for row in rows if row.state == "BENCHMARK_TASK_RUN_STATE_COMPLETED")
    boolean_passes = sum(1 for row in rows if row.passed)
    strict_clean_passes = sum(1 for row in rows if row.strict_clean_pass)
    clean_runs = sum(1 for row in rows if row.clean_run)
    lines = [
        f"{task_name} hosted 50-case legal expansion:",
        f"- Authoritative source: {source_name}",
        f"- Completed runs: {completed_runs}/{total_runs}",
        f"- Boolean passes: {boolean_passes}/{total_runs} = {format_pct(boolean_passes, total_runs)}",
        f"- Strict-clean passes: {strict_clean_passes}/{total_runs} = {format_pct(strict_clean_passes, total_runs)}",
        f"- Clean runs: {clean_runs}/{total_runs}",
        f"- All-pass cases: {all_pass_cases}/50",
        f"- All-fail cases: {all_fail_cases}/50",
        f"- Disagreement cases: {disagreement_cases}/50",
        "",
        "Per-model:",
    ]
    for stat in per_model_stats:
        lines.extend(
            [
                f"- {stat['model_label']}:",
                f"  boolean case pass: {stat['boolean_passes']}/{stat['case_count']} = "
                f"{format_pct(int(stat['boolean_passes']), int(stat['case_count']))}",
                f"  strict-clean case pass: {stat['strict_clean_passes']}/{stat['case_count']} = "
                f"{format_pct(int(stat['strict_clean_passes']), int(stat['case_count']))}",
                f"  clean runs: {stat['clean_runs']}/{stat['case_count']}",
                f"  runtime: {stat['total_seconds'] / 60:.1f} minutes total, {stat['avg_seconds']:.1f} seconds/case average",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_findings(
    path: Path,
    task_name: str,
    source_name: str,
    per_model_stats: list[dict[str, object]],
    all_pass_cases: int,
    all_fail_cases: int,
    disagreement_cases: int,
) -> None:
    total_runs = sum(int(stat["case_count"]) for stat in per_model_stats)
    boolean_passes = sum(int(stat["boolean_passes"]) for stat in per_model_stats)
    strict_clean_passes = sum(int(stat["strict_clean_passes"]) for stat in per_model_stats)
    clean_runs = sum(int(stat["clean_runs"]) for stat in per_model_stats)

    shared_hard_cases = None
    failed_case_sets = [set(row.case_id for row in stat["failed_cases"]) for stat in per_model_stats]
    if failed_case_sets:
        shared_hard_cases = sorted(set.intersection(*failed_case_sets))
    else:
        shared_hard_cases = []

    lines = [
        "# CUC Findings Legal v2 - hosted 50-case expansion",
        "",
        "## Source lock",
        f"- Authoritative source: `{source_name}`",
        f"- Task: `{task_name}`",
        "- Scope: hosted Kaggle run of the expanded 50-case legal-only benchmark.",
        "- Positioning rule: keep the locked 5-case legal pilot as the validated baseline; treat this hosted 50-case run as the next expansion study, not as a replacement proof point.",
        "",
        "## Headline results",
    ]
    for stat in per_model_stats:
        lines.append(
            f"- {stat['model_label']}: {stat['boolean_passes']}/{stat['case_count']} = "
            f"{format_pct(int(stat['boolean_passes']), int(stat['case_count']))}"
        )
    lines.extend(
        [
            "",
            "## Strongest safe claim",
            "The expanded hosted legal run validates the Kaggle execution path, but it also shows that the current 50-case set is too easy or too judge-lenient to be the final flagship benchmark without another discrimination pass.",
            "",
            "## Why this result should not replace the pilot",
            f"- {all_pass_cases}/50 cases are all-pass across all three models.",
            f"- Only {all_fail_cases}/50 cases are all-fail across all three models.",
            f"- Only {disagreement_cases}/50 cases produce cross-model separation.",
            f"- Clean-run hygiene is {clean_runs}/{total_runs}; {total_runs - clean_runs} runs showed one-judge or partial-criteria fragility.",
            f"- Strict-clean passes drop slightly to {strict_clean_passes}/{total_runs}, which is a reminder to keep scorer-shape issues visible in the writeup.",
            "",
            "## Shared hard cases",
        ]
    )
    for case_id in shared_hard_cases:
        lines.append(f"- `{case_id}`")

    lines.extend(
        [
            "",
            "## Model-specific failure read",
        ]
    )
    for stat in per_model_stats:
        failed_cases = ", ".join(f"`{row.case_id}` ({row.criteria_passed}/15)" for row in stat["failed_cases"])
        lines.append(f"- {stat['model_label']}: {failed_cases if failed_cases else 'none'}")

    lines.extend(
        [
            "",
            "## Scorer hygiene",
        ]
    )
    for stat in per_model_stats:
        malformed_cases = ", ".join(
            f"`{row.case_id}` ({row.criteria_total} criteria returned)"
            for row in stat["malformed_cases"]
        )
        lines.append(
            f"- {stat['model_label']}: {int(stat['clean_runs'])}/{int(stat['case_count'])} clean runs. "
            f"Non-clean runs: {malformed_cases if malformed_cases else 'none'}"
        )

    lines.extend(
        [
            "",
            "## Writeup-safe interpretation",
            "1. The hosted run demonstrates that the expanded legal bundle executes end to end in Kaggle at 50 cases.",
            "2. The current v2 scoring path still separates models, but the gap is much narrower than the validated 5-case pilot.",
            "3. The all-pass rate is high enough that we should not present this 50-case scoreboard as the final metacognition claim without another hardening pass.",
            "4. The best use of this run is diagnostic: identify easy cases, tighten cases with scorer-shape fragility, and rerun before deciding whether to scale to 100.",
            "",
            "## Next action",
            "Audit the 37 all-pass cases first, then tighten the weakest or most templated cases and rerun the hosted 50-case benchmark before promoting any new leaderboard claim.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_v4_flat_csv(path: Path, rows: list[V4CandidateRunRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model",
        "model_slug",
        "case_id",
        "passed",
        "state",
        "overall_pass",
        "overall_score",
        "hard_fail_reasons",
        "fabricated_ids_hard_fail",
        "fabricated_evidence_ids_hard_fail",
        "score_story_consistent",
        "assertion_fail_count",
        "axis_delta_detection",
        "axis_causal_temporal_propagation",
        "axis_selective_revision",
        "axis_unknown_ledger_discipline",
        "axis_evidence_grounding",
        "duration_seconds",
        "start_time",
        "end_time",
        "param_id",
        "file",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (item.model_label, item.param_id, item.case_id)):
            writer.writerow(
                {
                    "model": row.model_label,
                    "model_slug": row.model_slug,
                    "case_id": row.case_id,
                    "passed": row.passed,
                    "state": row.state,
                    "overall_pass": row.overall_pass,
                    "overall_score": f"{row.overall_score:.6f}",
                    "hard_fail_reasons": json.dumps(list(row.hard_fail_reasons)),
                    "fabricated_ids_hard_fail": row.fabricated_ids_hard_fail,
                    "fabricated_evidence_ids_hard_fail": row.fabricated_evidence_ids_hard_fail,
                    "score_story_consistent": row.score_story_consistent,
                    "assertion_fail_count": row.assertion_fail_count,
                    "axis_delta_detection": f"{row.axis_delta_detection:.6f}",
                    "axis_causal_temporal_propagation": f"{row.axis_causal_temporal_propagation:.6f}",
                    "axis_selective_revision": f"{row.axis_selective_revision:.6f}",
                    "axis_unknown_ledger_discipline": f"{row.axis_unknown_ledger_discipline:.6f}",
                    "axis_evidence_grounding": f"{row.axis_evidence_grounding:.6f}",
                    "duration_seconds": f"{row.duration_seconds:.3f}",
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "param_id": row.param_id,
                    "file": row.file_name,
                }
            )


def write_v4_case_matrix(path: Path, rows: list[V4CandidateRunRow]) -> tuple[int, int, int]:
    fieldnames = [
        "case_id",
        "passed",
        "overall_pass",
        "overall_score",
        "hard_fail_reasons",
        "fabricated_ids_hard_fail",
        "fabricated_evidence_ids_hard_fail",
        "score_story_consistent",
        "assertion_fail_count",
        "axis_delta_detection",
        "axis_causal_temporal_propagation",
        "axis_selective_revision",
        "axis_unknown_ledger_discipline",
        "axis_evidence_grounding",
    ]
    all_pass = 0
    all_fail = 0
    disagreements = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: item.case_id):
            all_pass += int(row.passed)
            all_fail += int(not row.passed)
            writer.writerow(
                {
                    "case_id": row.case_id,
                    "passed": row.passed,
                    "overall_pass": row.overall_pass,
                    "overall_score": f"{row.overall_score:.6f}",
                    "hard_fail_reasons": json.dumps(list(row.hard_fail_reasons)),
                    "fabricated_ids_hard_fail": row.fabricated_ids_hard_fail,
                    "fabricated_evidence_ids_hard_fail": row.fabricated_evidence_ids_hard_fail,
                    "score_story_consistent": row.score_story_consistent,
                    "assertion_fail_count": row.assertion_fail_count,
                    "axis_delta_detection": f"{row.axis_delta_detection:.6f}",
                    "axis_causal_temporal_propagation": f"{row.axis_causal_temporal_propagation:.6f}",
                    "axis_selective_revision": f"{row.axis_selective_revision:.6f}",
                    "axis_unknown_ledger_discipline": f"{row.axis_unknown_ledger_discipline:.6f}",
                    "axis_evidence_grounding": f"{row.axis_evidence_grounding:.6f}",
                }
            )
    return all_pass, all_fail, disagreements


def write_v4_headline_metrics(
    path: Path,
    task_name: str,
    source_name: str,
    rows: list[V4CandidateRunRow],
) -> None:
    total_runs = len(rows)
    completed_runs = sum(
        1 for row in rows if row.state == "BENCHMARK_TASK_RUN_STATE_COMPLETED"
    )
    passed_runs = sum(1 for row in rows if row.passed)
    fabricated_regressions = sum(
        1
        for row in rows
        if row.fabricated_ids_hard_fail or row.fabricated_evidence_ids_hard_fail
    )
    hard_fail_union = sorted({reason for row in rows for reason in row.hard_fail_reasons})
    inconsistencies = sum(1 for row in rows if not row.score_story_consistent)
    lines = [
        f"{task_name} v4 candidate import ({source_name})",
        f"- Completed runs: {completed_runs}/{total_runs}",
        f"- Passed runs: {passed_runs}/{total_runs} = {format_pct(passed_runs, total_runs)}",
        f"- Fabricated-id regressions: {fabricated_regressions}",
        f"- Score/export inconsistencies: {inconsistencies}",
        f"- Hard-fail reasons seen: {', '.join(hard_fail_union) if hard_fail_union else 'none'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_v4_summary(
    path: Path,
    task_name: str,
    source_name: str,
    rows: list[V4CandidateRunRow],
) -> None:
    total_runs = len(rows)
    completed_runs = sum(
        1 for row in rows if row.state == "BENCHMARK_TASK_RUN_STATE_COMPLETED"
    )
    passed_runs = sum(1 for row in rows if row.passed)
    hard_fail_union = sorted({reason for row in rows for reason in row.hard_fail_reasons})
    lines = [
        f"{task_name} v4 candidate import:",
        f"- Authoritative source: {source_name}",
        f"- Completed runs: {completed_runs}/{total_runs}",
        f"- Passed runs: {passed_runs}/{total_runs} = {format_pct(passed_runs, total_runs)}",
        f"- Hard-fail reasons seen: {', '.join(hard_fail_union) if hard_fail_union else 'none'}",
        "- Per-case pass summary:",
    ]
    for row in sorted(rows, key=lambda item: item.case_id):
        lines.append(
            f"  - {row.case_id}: passed={row.passed}, overall_score={row.overall_score:.6f}, "
            f"hard_fail_reasons={list(row.hard_fail_reasons) if row.hard_fail_reasons else []}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_v4_findings(
    path: Path,
    task_name: str,
    source_name: str,
    rows: list[V4CandidateRunRow],
) -> None:
    passed_runs = sum(1 for row in rows if row.passed)
    fabricated_regressions = [
        row.case_id
        for row in rows
        if row.fabricated_ids_hard_fail or row.fabricated_evidence_ids_hard_fail
    ]
    inconsistent_cases = [
        row.case_id for row in rows if not row.score_story_consistent
    ]
    lines = [
        "# CUC Findings v4 Candidate import",
        "",
        "## Source lock",
        f"- Authoritative source: `{source_name}`",
        f"- Task: `{task_name}`",
        "- Scope: imported Kaggle results for the 2-case v4 candidate preserve-heavy pilot.",
        "",
        "## Headline result",
        f"- Case pass count: {passed_runs}/{len(rows)}",
        f"- Fabricated-id regressions: {', '.join(f'`{case}`' for case in fabricated_regressions) if fabricated_regressions else 'none'}",
        f"- Score/export inconsistencies: {', '.join(f'`{case}`' for case in inconsistent_cases) if inconsistent_cases else 'none'}",
        "",
        "## Case summary",
    ]
    for row in sorted(rows, key=lambda item: item.case_id):
        lines.append(
            f"- `{row.case_id}`: passed={row.passed}, overall_score={row.overall_score:.6f}, "
            f"hard_fail_reasons={list(row.hard_fail_reasons) if row.hard_fail_reasons else []}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    task_name, rows = load_run_rows(zip_path=args.zip_path, results_dir=args.results_dir)
    source_name = (
        args.zip_path.name
        if args.zip_path is not None
        else args.results_dir.name
    )
    if not rows:
        raise RuntimeError(f"No .run.json files found in {source_name}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.doc_dir.mkdir(parents=True, exist_ok=True)

    flat_csv = args.output_dir / f"cuc_results_flat_{args.prefix}.csv"
    case_matrix_csv = args.output_dir / f"{args.prefix}_case_matrix.csv"
    headline_path = args.output_dir / f"{args.prefix}_headline_metrics.txt"
    summary_path = args.output_dir / f"{args.prefix}_summary.txt"
    findings_path = args.doc_dir / f"CUC_findings_{args.prefix}.md"

    if task_name == "cuc_metacognition_v4_candidate":
        _, v4_rows = load_v4_candidate_run_rows(
            zip_path=args.zip_path,
            results_dir=args.results_dir,
        )
        write_v4_flat_csv(flat_csv, v4_rows)
        write_v4_case_matrix(case_matrix_csv, v4_rows)
        write_v4_headline_metrics(headline_path, task_name, source_name, v4_rows)
        write_v4_summary(summary_path, task_name, source_name, v4_rows)
        write_v4_findings(findings_path, task_name, source_name, v4_rows)

        print(f"Wrote {flat_csv}")
        print(f"Wrote {case_matrix_csv}")
        print(f"Wrote {headline_path}")
        print(f"Wrote {summary_path}")
        print(f"Wrote {findings_path}")
        return

    per_model_stats = build_per_model_stats(rows)
    write_flat_csv(flat_csv, rows)
    all_pass_cases, all_fail_cases, disagreement_cases = write_case_matrix(case_matrix_csv, rows)
    write_headline_metrics(
        headline_path,
        task_name,
        source_name,
        rows,
        per_model_stats,
        all_pass_cases,
        all_fail_cases,
        disagreement_cases,
    )
    write_summary(
        summary_path,
        task_name,
        source_name,
        rows,
        per_model_stats,
        all_pass_cases,
        all_fail_cases,
        disagreement_cases,
    )
    write_findings(
        findings_path,
        task_name,
        source_name,
        per_model_stats,
        all_pass_cases,
        all_fail_cases,
        disagreement_cases,
    )

    print(f"Wrote {flat_csv}")
    print(f"Wrote {case_matrix_csv}")
    print(f"Wrote {headline_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {findings_path}")


if __name__ == "__main__":
    main()
