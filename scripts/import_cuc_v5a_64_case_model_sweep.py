from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from import_cuc_kaggle_results_zip import MODEL_COLUMN_KEYS, MODEL_LABELS


TASK_NAME = "cuc_metacognition_v5a_candidate"
DIAGNOSTIC_PREFIX = "V5A_PRIOR_ANCHOR_DIAGNOSTICS="
DEFAULT_PREFIX = "cuc_v5a_64_case_sweep_2026_04_14"
DEFAULT_OUTPUT_DIR = Path("cuc-results")
DEFAULT_DOC_DIR = Path("cuc-docs")
COMPLETED_STATUS = "success"


@dataclass(frozen=True)
class V5ARunRow:
    case_id: str
    source_case_id: str | None
    family_id: str
    sector_skin: str
    render_profile: str
    hop_depth: int
    v5a_pilot_bucket: str
    model_slug: str
    model_label: str
    zip_path: str
    exported_at_utc: str
    task_passed: bool
    run2a_pass: bool
    run2b_pass: bool
    run2a_score: float
    run2b_score: float
    scaffold_case: bool
    reverse_scaffold_case: bool
    both_fail: bool
    citation_key_delta: int
    citation_coverage_delta: float
    prior_anchor_suspected: bool
    status: str


@dataclass(frozen=True)
class V5ABundle:
    zip_path: Path
    exported_at_utc: str
    model_slug: str
    model_label: str
    rows: tuple[V5ARunRow, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import a completed CUC v5a 64-case model sweep from Kaggle results zips "
            "and write repo-side summary artifacts."
        )
    )
    parser.add_argument(
        "--zip-path",
        dest="zip_paths",
        type=Path,
        nargs="+",
        required=True,
        help="One or more Kaggle results.zip files to import.",
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
        help="Directory for generated markdown artifacts.",
    )
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help="Prefix for generated artifact filenames.",
    )
    return parser.parse_args()


def parse_timestamp(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def load_results_export(zip_path: Path) -> dict[str, Any]:
    with ZipFile(zip_path) as archive:
        export_name = next(
            (name for name in archive.namelist() if name.endswith("results_export.json")),
            None,
        )
        if export_name is None:
            raise RuntimeError(f"{zip_path} does not contain results_export.json")
        return json.loads(archive.read(export_name).decode("utf-8"))


def parse_diagnostic_payload(assertion_results: list[dict[str, Any]]) -> dict[str, Any]:
    for assertion in assertion_results:
        expectation = str(assertion.get("expectation", ""))
        if expectation.startswith(DIAGNOSTIC_PREFIX):
            return json.loads(expectation.split("=", 1)[1])
    raise RuntimeError("Run assertion payload missing V5A_PRIOR_ANCHOR_DIAGNOSTICS marker")


def load_bundle(zip_path: Path) -> V5ABundle:
    payload = load_results_export(zip_path)
    if payload.get("task_name") != TASK_NAME:
        raise RuntimeError(f"{zip_path} is not a {TASK_NAME} export")
    runs = list(payload.get("runs", []))
    if not runs:
        raise RuntimeError(f"{zip_path} contains no runs")

    model_slug = str(runs[0].get("llm"))
    model_label = MODEL_LABELS.get(model_slug, model_slug)
    exported_at_utc = str(payload.get("exported_at_utc", ""))

    rows: list[V5ARunRow] = []
    for run in runs:
        diagnostic_payload = parse_diagnostic_payload(list(run.get("assertion_results", [])))
        diagnostics = diagnostic_payload["diagnostics"]
        run2a_pass = bool(diagnostic_payload["run2a_overall_pass"])
        run2b_pass = bool(diagnostic_payload["run2b_overall_pass"])
        rows.append(
            V5ARunRow(
                case_id=str(run.get("case_id")),
                source_case_id=run.get("source_case_id"),
                family_id=str(run.get("family_id")),
                sector_skin=str(run.get("sector_skin")),
                render_profile=str(run.get("render_profile")),
                hop_depth=int(run.get("hop_depth")),
                v5a_pilot_bucket=str(run.get("v5a_pilot_bucket")),
                model_slug=model_slug,
                model_label=model_label,
                zip_path=str(zip_path),
                exported_at_utc=exported_at_utc,
                task_passed=bool(run.get("passed")),
                run2a_pass=run2a_pass,
                run2b_pass=run2b_pass,
                run2a_score=float(diagnostic_payload["run2a_overall_score"]),
                run2b_score=float(diagnostic_payload["run2b_overall_score"]),
                scaffold_case=run2a_pass and not run2b_pass,
                reverse_scaffold_case=run2b_pass and not run2a_pass,
                both_fail=(not run2a_pass) and (not run2b_pass),
                citation_key_delta=int(diagnostics["citation_key_delta"]),
                citation_coverage_delta=float(diagnostics["citation_coverage_delta"]),
                prior_anchor_suspected=bool(diagnostics["prior_anchor_suspected"]),
                status=str(run.get("status")),
            )
        )
    return V5ABundle(
        zip_path=zip_path,
        exported_at_utc=exported_at_utc,
        model_slug=model_slug,
        model_label=model_label,
        rows=tuple(sorted(rows, key=lambda row: row.case_id)),
    )


def dedupe_bundles(bundles: list[V5ABundle]) -> tuple[list[V5ABundle], dict[str, list[str]]]:
    latest_by_slug: dict[str, V5ABundle] = {}
    duplicates: dict[str, list[str]] = defaultdict(list)
    for bundle in sorted(
        bundles,
        key=lambda item: (parse_timestamp(item.exported_at_utc), item.zip_path.name),
    ):
        current = latest_by_slug.get(bundle.model_slug)
        if current is None:
            latest_by_slug[bundle.model_slug] = bundle
            continue
        duplicates[bundle.model_label].append(str(current.zip_path))
        latest_by_slug[bundle.model_slug] = bundle
    selected = sorted(latest_by_slug.values(), key=lambda item: item.model_label)
    for bundle in selected:
        duplicates[bundle.model_label] = [
            path for path in duplicates.get(bundle.model_label, []) if path != str(bundle.zip_path)
        ]
    duplicates = {label: paths for label, paths in duplicates.items() if paths}
    return selected, duplicates


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_flat_csv(path: Path, rows: list[V5ARunRow]) -> None:
    write_csv(
        path,
        [
            "case_id",
            "source_case_id",
            "family_id",
            "sector_skin",
            "render_profile",
            "hop_depth",
            "v5a_pilot_bucket",
            "model",
            "model_slug",
            "zip_path",
            "exported_at_utc",
            "task_passed",
            "run2a_pass",
            "run2b_pass",
            "run2a_score",
            "run2b_score",
            "scaffold_case",
            "reverse_scaffold_case",
            "both_fail",
            "citation_key_delta",
            "citation_coverage_delta",
            "prior_anchor_suspected",
            "status",
        ],
        [
            {
                "case_id": row.case_id,
                "source_case_id": row.source_case_id or "",
                "family_id": row.family_id,
                "sector_skin": row.sector_skin,
                "render_profile": row.render_profile,
                "hop_depth": row.hop_depth,
                "v5a_pilot_bucket": row.v5a_pilot_bucket,
                "model": row.model_label,
                "model_slug": row.model_slug,
                "zip_path": row.zip_path,
                "exported_at_utc": row.exported_at_utc,
                "task_passed": row.task_passed,
                "run2a_pass": row.run2a_pass,
                "run2b_pass": row.run2b_pass,
                "run2a_score": f"{row.run2a_score:.6f}",
                "run2b_score": f"{row.run2b_score:.6f}",
                "scaffold_case": row.scaffold_case,
                "reverse_scaffold_case": row.reverse_scaffold_case,
                "both_fail": row.both_fail,
                "citation_key_delta": row.citation_key_delta,
                "citation_coverage_delta": f"{row.citation_coverage_delta:.6f}",
                "prior_anchor_suspected": row.prior_anchor_suspected,
                "status": row.status,
            }
            for row in rows
        ],
    )


def write_model_summary_csv(path: Path, bundles: list[V5ABundle]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for bundle in sorted(bundles, key=lambda item: item.model_label):
        run_rows = list(bundle.rows)
        case_count = len(run_rows)
        task_pass_count = sum(1 for row in run_rows if row.task_passed)
        run2a_pass_count = sum(1 for row in run_rows if row.run2a_pass)
        run2b_pass_count = sum(1 for row in run_rows if row.run2b_pass)
        scaffold_cases = sum(1 for row in run_rows if row.scaffold_case)
        reverse_scaffold_cases = sum(1 for row in run_rows if row.reverse_scaffold_case)
        both_fail_cases = sum(1 for row in run_rows if row.both_fail)
        consistent_task_result_count = sum(
            1
            for row in run_rows
            if row.task_passed == (row.run2a_pass and row.run2b_pass)
        )
        avg_key_delta = sum(row.citation_key_delta for row in run_rows) / case_count
        avg_cov_delta = sum(row.citation_coverage_delta for row in run_rows) / case_count
        rows.append(
            {
                "model": bundle.model_label,
                "model_slug": bundle.model_slug,
                "zip_path": str(bundle.zip_path),
                "exported_at_utc": bundle.exported_at_utc,
                "case_count": case_count,
                "task_pass_count": task_pass_count,
                "task_fail_count": case_count - task_pass_count,
                "task_pass_rate": f"{(task_pass_count / case_count) * 100:.1f}%",
                "run2a_pass_count": run2a_pass_count,
                "run2b_pass_count": run2b_pass_count,
                "run2a_pass_rate": f"{(run2a_pass_count / case_count) * 100:.1f}%",
                "run2b_pass_rate": f"{(run2b_pass_count / case_count) * 100:.1f}%",
                "advantage_cases": run2a_pass_count - run2b_pass_count,
                "advantage_pp": f"{((run2a_pass_count - run2b_pass_count) / case_count) * 100:.1f}",
                "scaffold_cases": scaffold_cases,
                "reverse_scaffold_cases": reverse_scaffold_cases,
                "both_fail_cases": both_fail_cases,
                "avg_citation_key_delta": f"{avg_key_delta:.2f}",
                "avg_citation_coverage_delta": f"{avg_cov_delta:.3f}",
                "all_task_results_consistent": consistent_task_result_count == case_count,
            }
        )
    rows.sort(
        key=lambda item: (
            -int(item["run2a_pass_count"]),
            -int(item["run2b_pass_count"]),
            str(item["model"]),
        )
    )
    write_csv(
        path,
        list(rows[0].keys()) if rows else [],
        rows,
    )
    return rows


def write_case_matrix_csv(path: Path, rows: list[V5ARunRow], model_order: list[str]) -> tuple[int, int]:
    case_rows: dict[str, dict[str, V5ARunRow]] = defaultdict(dict)
    case_meta: dict[str, V5ARunRow] = {}
    for row in rows:
        case_rows[row.case_id][row.model_slug] = row
        case_meta.setdefault(row.case_id, row)

    fieldnames = [
        "case_id",
        "source_case_id",
        "family_id",
        "sector_skin",
        "render_profile",
        "hop_depth",
        "v5a_pilot_bucket",
    ]
    for slug in model_order:
        key = MODEL_COLUMN_KEYS.get(slug, slug.replace("/", "_").replace(".", "_"))
        fieldnames.extend(
            [
                f"{key}_task_passed",
                f"{key}_run2a_pass",
                f"{key}_run2b_pass",
                f"{key}_citation_key_delta",
            ]
        )
    fieldnames.extend(
        [
            "task_pass_model_count",
            "run2a_pass_model_count",
            "run2b_pass_model_count",
            "scaffold_model_count",
            "reverse_scaffold_model_count",
            "both_fail_model_count",
            "all_models_task_passed",
            "all_models_task_failed",
        ]
    )

    all_task_pass = 0
    all_task_fail = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for case_id in sorted(case_rows):
            meta = case_meta[case_id]
            out: dict[str, object] = {
                "case_id": case_id,
                "source_case_id": meta.source_case_id or "",
                "family_id": meta.family_id,
                "sector_skin": meta.sector_skin,
                "render_profile": meta.render_profile,
                "hop_depth": meta.hop_depth,
                "v5a_pilot_bucket": meta.v5a_pilot_bucket,
            }
            task_pass_values: list[bool] = []
            for slug in model_order:
                key = MODEL_COLUMN_KEYS.get(slug, slug.replace("/", "_").replace(".", "_"))
                row = case_rows[case_id].get(slug)
                if row is None:
                    out[f"{key}_task_passed"] = ""
                    out[f"{key}_run2a_pass"] = ""
                    out[f"{key}_run2b_pass"] = ""
                    out[f"{key}_citation_key_delta"] = ""
                    continue
                task_pass_values.append(row.task_passed)
                out[f"{key}_task_passed"] = row.task_passed
                out[f"{key}_run2a_pass"] = row.run2a_pass
                out[f"{key}_run2b_pass"] = row.run2b_pass
                out[f"{key}_citation_key_delta"] = row.citation_key_delta

            rows_for_case = list(case_rows[case_id].values())
            out["task_pass_model_count"] = sum(1 for row in rows_for_case if row.task_passed)
            out["run2a_pass_model_count"] = sum(1 for row in rows_for_case if row.run2a_pass)
            out["run2b_pass_model_count"] = sum(1 for row in rows_for_case if row.run2b_pass)
            out["scaffold_model_count"] = sum(1 for row in rows_for_case if row.scaffold_case)
            out["reverse_scaffold_model_count"] = sum(
                1 for row in rows_for_case if row.reverse_scaffold_case
            )
            out["both_fail_model_count"] = sum(1 for row in rows_for_case if row.both_fail)
            out["all_models_task_passed"] = bool(task_pass_values) and all(task_pass_values)
            out["all_models_task_failed"] = bool(task_pass_values) and not any(task_pass_values)
            all_task_pass += int(bool(out["all_models_task_passed"]))
            all_task_fail += int(bool(out["all_models_task_failed"]))
            writer.writerow(out)
    return all_task_pass, all_task_fail


def write_family_summary_csv(path: Path, rows: list[V5ARunRow]) -> list[dict[str, object]]:
    grouped: dict[str, list[V5ARunRow]] = defaultdict(list)
    for row in rows:
        grouped[row.family_id].append(row)
    out_rows: list[dict[str, object]] = []
    for family_id, group_rows in sorted(grouped.items()):
        total = len(group_rows)
        run2a_pass = sum(1 for row in group_rows if row.run2a_pass)
        run2b_pass = sum(1 for row in group_rows if row.run2b_pass)
        out_rows.append(
            {
                "family_id": family_id,
                "model_case_pairs": total,
                "distinct_cases": len({row.case_id for row in group_rows}),
                "run2a_pass_count": run2a_pass,
                "run2b_pass_count": run2b_pass,
                "run2a_pass_rate": f"{run2a_pass / total:.3f}",
                "run2b_pass_rate": f"{run2b_pass / total:.3f}",
                "scaffold_cases": sum(1 for row in group_rows if row.scaffold_case),
                "reverse_scaffold_cases": sum(
                    1 for row in group_rows if row.reverse_scaffold_case
                ),
                "both_fail_cases": sum(1 for row in group_rows if row.both_fail),
            }
        )
    write_csv(path, list(out_rows[0].keys()) if out_rows else [], out_rows)
    return out_rows


def write_headline_metrics(
    path: Path,
    model_rows: list[dict[str, object]],
    all_task_pass: int,
    all_task_fail: int,
    total_cases: int,
    duplicate_count: int,
) -> None:
    lines = [
        "CUC v5a 64-case sweep import",
        f"- Distinct imported models: {len(model_rows)}",
        f"- Duplicate zips ignored: {duplicate_count}",
        f"- Cases per model: {total_cases}",
        f"- All-model task-pass cases: {all_task_pass}/{total_cases}",
        f"- All-model task-fail cases: {all_task_fail}/{total_cases}",
    ]
    for row in model_rows:
        lines.append(
            f"- {row['model']}: 2A {row['run2a_pass_count']}/{row['case_count']}, "
            f"2B {row['run2b_pass_count']}/{row['case_count']}, "
            f"task {row['task_pass_count']}/{row['case_count']}, "
            f"advantage={row['advantage_pp']}pp"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_doc(
    path: Path,
    prefix: str,
    bundles: list[V5ABundle],
    model_rows: list[dict[str, object]],
    family_rows: list[dict[str, object]],
    duplicates: dict[str, list[str]],
    all_task_pass: int,
    all_task_fail: int,
    total_cases: int,
    output_dir: Path,
) -> None:
    positive_advantage = [
        row["model"]
        for row in model_rows
        if int(row["run2a_pass_count"]) > int(row["run2b_pass_count"])
    ]
    neutral_advantage = [
        row["model"]
        for row in model_rows
        if int(row["run2a_pass_count"]) == int(row["run2b_pass_count"])
    ]
    reverse_advantage = [
        row["model"]
        for row in model_rows
        if int(row["run2a_pass_count"]) < int(row["run2b_pass_count"])
    ]
    evidence_removal_row = next(
        (row for row in family_rows if row["family_id"] == "evidence_removal"),
        None,
    )
    threshold_row = next(
        (row for row in family_rows if row["family_id"] == "threshold_crossing"),
        None,
    )
    lines = [
        "# CUC v5a 64-Case Sweep",
        "",
        "## Source lock",
        f"- Task: `{TASK_NAME}`",
        f"- Canonical repo task: `benchmark/cuc_metacognition_v5a_candidate.task.json`",
        f"- Canonical repo full-pack params: `benchmark/cuc_v5_64_params.json`",
        f"- Distinct imported models: {len(bundles)}",
        f"- Duplicate zips skipped: {sum(len(paths) for paths in duplicates.values())}",
        f"- Duplicate detail: {', '.join(f'{label}: {len(paths)} skipped' for label, paths in sorted(duplicates.items())) if duplicates else 'none'}",
        "",
        "## Model results",
    ]
    for row in model_rows:
        lines.append(
            f"- {row['model']}: 2A {row['run2a_pass_count']}/{row['case_count']} "
            f"({row['run2a_pass_rate']}), 2B {row['run2b_pass_count']}/{row['case_count']} "
            f"({row['run2b_pass_rate']}), task {row['task_pass_count']}/{row['case_count']} "
            f"({row['task_pass_rate']}), scaffold cases={row['scaffold_cases']}, "
            f"reverse-scaffold cases={row['reverse_scaffold_cases']}"
        )
    lines.extend(
        [
            "",
            "## Supported read",
            f"- Positive prior advantage appears in {len(positive_advantage)}/{len(model_rows)} models: {', '.join(positive_advantage) if positive_advantage else 'none'}.",
            f"- Neutral prior advantage models: {', '.join(neutral_advantage) if neutral_advantage else 'none'}.",
            f"- Counterexample models where 2B beats 2A: {', '.join(reverse_advantage) if reverse_advantage else 'none'}.",
            f"- All-model task-pass cases: {all_task_pass}/{total_cases}.",
            f"- All-model task-fail cases: {all_task_fail}/{total_cases}.",
        ]
    )
    if evidence_removal_row is not None:
        lines.append(
            f"- `evidence_removal` is the universal hard family: "
            f"2A {evidence_removal_row['run2a_pass_count']}/{evidence_removal_row['model_case_pairs']}, "
            f"2B {evidence_removal_row['run2b_pass_count']}/{evidence_removal_row['model_case_pairs']}."
        )
    if threshold_row is not None:
        lines.append(
            f"- `threshold_crossing` is the strongest scaffold-sensitive family: "
            f"2A {threshold_row['run2a_pass_count']}/{threshold_row['model_case_pairs']}, "
            f"2B {threshold_row['run2b_pass_count']}/{threshold_row['model_case_pairs']}."
        )
    lines.extend(
        [
            "",
            "## Cautions",
            "- This sweep supports a scaffold-sensitive selective belief revision story, not a universal prior-as-scaffold law.",
            "- The strongest counterexample is Gemma 4 26B, which does better on 2B than 2A.",
            "- No-op controls are not universally scaffold-sensitive; the dramatic no-op dependence is concentrated in Gemini 2.5 Pro.",
            "- This is still a two-evidence-state benchmark. It does not yet prove sequential multi-step truth maintenance.",
            "",
            "## Generated artifacts",
            f"- [flat runs csv]({(output_dir / f'cuc_results_flat_{prefix}.csv').as_posix()})",
            f"- [model summary csv]({(output_dir / f'{prefix}_model_summary.csv').as_posix()})",
            f"- [case matrix csv]({(output_dir / f'{prefix}_case_matrix.csv').as_posix()})",
            f"- [family summary csv]({(output_dir / f'{prefix}_family_summary.csv').as_posix()})",
            f"- [headline metrics txt]({(output_dir / f'{prefix}_headline_metrics.txt').as_posix()})",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.doc_dir.mkdir(parents=True, exist_ok=True)

    raw_bundles = [load_bundle(path) for path in args.zip_paths]
    bundles, duplicates = dedupe_bundles(raw_bundles)
    rows = [row for bundle in bundles for row in bundle.rows]
    if not rows:
        raise RuntimeError("No v5a rows found in the supplied zips")

    flat_csv = args.output_dir / f"cuc_results_flat_{args.prefix}.csv"
    model_summary_csv = args.output_dir / f"{args.prefix}_model_summary.csv"
    case_matrix_csv = args.output_dir / f"{args.prefix}_case_matrix.csv"
    family_summary_csv = args.output_dir / f"{args.prefix}_family_summary.csv"
    headline_metrics_txt = args.output_dir / f"{args.prefix}_headline_metrics.txt"
    doc_path = args.doc_dir / "CUC_V5A_64_CASE_SWEEP_2026_04_14.md"

    write_flat_csv(flat_csv, rows)
    model_rows = write_model_summary_csv(model_summary_csv, bundles)
    all_task_pass, all_task_fail = write_case_matrix_csv(
        case_matrix_csv,
        rows,
        [bundle.model_slug for bundle in bundles],
    )
    family_rows = write_family_summary_csv(family_summary_csv, rows)
    total_cases = len({row.case_id for row in rows})
    write_headline_metrics(
        headline_metrics_txt,
        model_rows,
        all_task_pass,
        all_task_fail,
        total_cases,
        sum(len(paths) for paths in duplicates.values()),
    )
    write_summary_doc(
        doc_path,
        args.prefix,
        bundles,
        model_rows,
        family_rows,
        duplicates,
        all_task_pass,
        all_task_fail,
        total_cases,
        args.output_dir,
    )

    print(f"Wrote {flat_csv}")
    print(f"Wrote {model_summary_csv}")
    print(f"Wrote {case_matrix_csv}")
    print(f"Wrote {family_summary_csv}")
    print(f"Wrote {headline_metrics_txt}")
    print(f"Wrote {doc_path}")


if __name__ == "__main__":
    main()
