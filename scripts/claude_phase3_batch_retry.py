from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts.claude_phase3_diagnostic_retry import (  # noqa: E402
    DEFAULT_OUTPUT_DIR as SINGLE_CASE_OUTPUT_DIR,
)
from scripts.claude_phase3_diagnostic_retry import (  # noqa: E402
    DIAGNOSTIC_CLASSES,
    build_proposer,
    classify_failure_family,
    run_diagnostic_retry,
)

from core.cuc_harness.verifier import DeltaVerificationResult  # noqa: E402

DEFAULT_PARAMS_PATH = REPO_ROOT / "benchmark" / "cuc_v5_64_params.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cuc-results" / "claude_phase3_batch_retry"
DEFAULT_RESULTS_DIR = REPO_ROOT / "cuc-docs" / "batch_retry_results"
DEFAULT_PROOF_DIR = REPO_ROOT / "cuc-docs"
EXPECTED_CASE_COUNT = 64
SCHEMA_VERSION = "iv.cuc_harness.claude_phase3_batch_retry.v1"


@dataclass(frozen=True)
class BatchCaseSpec:
    case_id: str
    source_case_id: str
    fixture_dir: Path
    clean_pack: Mapping[str, Any]
    perturbed_pack: Mapping[str, Any]
    expected_delta: Mapping[str, Any]


def discover_case_specs(
    params_json: Path = DEFAULT_PARAMS_PATH,
    case_filters: Sequence[str] | None = None,
) -> list[BatchCaseSpec]:
    records = _load_param_records(params_json)
    by_id = {str(record["case_id"]): record for record in records}
    requested_ids = list(case_filters) if case_filters else list(by_id)
    missing = [case_id for case_id in requested_ids if case_id not in by_id]
    if missing:
        raise ValueError(f"case_id not found in {params_json}: {', '.join(missing)}")
    if not case_filters and len(requested_ids) != EXPECTED_CASE_COUNT:
        raise ValueError(
            f"expected {EXPECTED_CASE_COUNT} CUC cases from {params_json}, "
            f"found {len(requested_ids)}"
        )
    return [_case_spec_from_record(by_id[case_id]) for case_id in requested_ids]


def run_batch_retry(
    *,
    params_json: Path,
    baseline_dir: Path,
    output_dir: Path,
    ledger_root: Path,
    results_dir: Path,
    proof_dir: Path,
    proposer_args: argparse.Namespace,
    case_filters: Sequence[str] | None = None,
    dry_run: bool,
    run_date: str | None = None,
) -> dict[str, Any]:
    specs = discover_case_specs(params_json, case_filters)
    results_dir.mkdir(parents=True, exist_ok=True)
    proof_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_root.mkdir(parents=True, exist_ok=True)

    case_results: list[dict[str, Any]] = []
    for spec in specs:
        raw_result = _run_or_synthesize_case(
            spec=spec,
            baseline_dir=baseline_dir,
            output_dir=output_dir,
            ledger_root=ledger_root,
            proposer_args=proposer_args,
            dry_run=dry_run,
        )
        case_result = normalize_case_result(raw_result)
        case_result_path = results_dir / f"{_safe_name(spec.case_id)}_retry_result.json"
        _write_json(case_result_path, case_result)
        case_results.append(case_result)

    proof = build_batch_proof(
        case_results=case_results,
        run_date=run_date or _utc_date(),
        dry_run=dry_run,
        params_json=params_json,
        output_dir=output_dir,
        ledger_root=ledger_root,
        results_dir=results_dir,
    )
    proof_path = proof_dir / f"CLAUDE_PHASE3_BATCH_RETRY_PROOF_{proof['run_date']}.json"
    write_batch_proof(proof_path, proof)
    print(json.dumps(proof, indent=2, sort_keys=True, ensure_ascii=False))
    return proof


def normalize_case_result(raw_result: Mapping[str, Any]) -> dict[str, Any]:
    baseline = _mapping(raw_result.get("baseline"))
    retry = _mapping(raw_result.get("retry"))
    baseline_accepted = bool(baseline.get("accepted", False))
    retry_called = bool(retry.get("called", False))
    retry_accepted = bool(retry.get("accepted", False)) if retry_called else None
    baseline_similarity = _summary_similarity(baseline.get("gap_summary"))
    retry_similarity = _summary_similarity(retry.get("gap_summary"))
    similarity_delta = (
        round(retry_similarity - baseline_similarity, 6)
        if baseline_similarity is not None and retry_similarity is not None
        else None
    )
    baseline_reasons = _string_list(baseline.get("reasons"))
    baseline_families = _string_list(baseline.get("reason_families"))
    diagnostic_class = str(raw_result.get("diagnostic_class") or "")
    if not diagnostic_class:
        diagnostic_class = (
            "ACCEPTED"
            if baseline_accepted
            else classify_failure_family(
                DeltaVerificationResult(
                    accepted=False,
                    issues=tuple(
                        _issue_from_family(family) for family in baseline_families
                    ),
                ),
                {},
            )
        )
    if diagnostic_class == "UNCLASSIFIED":
        raise ValueError(f"unclassified diagnostic result for {raw_result['case_id']}")

    terminal_class = None
    terminal_reasons: list[str] = []
    if retry_called and retry_accepted is False:
        terminal_reasons = _string_list(retry.get("reasons"))
        terminal_class = _classify_terminal_retry(retry)

    return {
        "schema_version": f"{SCHEMA_VERSION}.case_result",
        "case_id": str(raw_result["case_id"]),
        "source_case_id": str(raw_result.get("source_case_id", "")),
        "fixture_dir": str(raw_result.get("fixture_dir", "")),
        "dry_run_source": raw_result.get("dry_run_source"),
        "baseline_accepted": baseline_accepted,
        "baseline_similarity": baseline_similarity,
        "baseline_reasons": baseline_reasons,
        "baseline_reason_families": baseline_families,
        "diagnostic_class": diagnostic_class,
        "retry_called": retry_called,
        "retry_accepted": retry_accepted,
        "retry_similarity": retry_similarity,
        "similarity_delta": similarity_delta,
        "terminal_diagnostic_class": terminal_class,
        "terminal_failure_reasons": terminal_reasons,
        "ledger_committed": bool(retry.get("ledger_committed", False)),
        "ledger_commit": retry.get("ledger_commit"),
    }


def build_batch_proof(
    *,
    case_results: Sequence[Mapping[str, Any]],
    run_date: str,
    dry_run: bool,
    params_json: Path,
    output_dir: Path,
    ledger_root: Path,
    results_dir: Path,
) -> dict[str, Any]:
    baseline_rejected = [
        result for result in case_results if not bool(result["baseline_accepted"])
    ]
    retry_attempts = [
        result for result in baseline_rejected if bool(result["retry_called"])
    ]
    retry_accepted = [
        result for result in retry_attempts if bool(result["retry_accepted"])
    ]
    committed = [
        result for result in retry_attempts if bool(result["ledger_committed"])
    ]
    deltas = [
        float(result["similarity_delta"])
        for result in retry_attempts
        if isinstance(result.get("similarity_delta"), (int, float))
    ]
    breakdown = {diagnostic_class: 0 for diagnostic_class in DIAGNOSTIC_CLASSES}
    breakdown["UNCLASSIFIED"] = 0
    for result in case_results:
        diagnostic_class = str(result["diagnostic_class"])
        if diagnostic_class == "UNCLASSIFIED":
            raise ValueError(f"unclassified case result: {result['case_id']}")
        breakdown[diagnostic_class] = breakdown.get(diagnostic_class, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "run_date": run_date,
        "dry_run": dry_run,
        "params_path": params_json.as_posix(),
        "output_dir": output_dir.as_posix(),
        "ledger_root": ledger_root.as_posix(),
        "results_dir": results_dir.as_posix(),
        "total_cases": len(case_results),
        "baseline_accepted": _count_rate(
            sum(1 for result in case_results if result["baseline_accepted"]),
            len(case_results),
        ),
        "retry_accepted": _count_rate(len(retry_accepted), len(baseline_rejected)),
        "retry_attempted": _count_rate(len(retry_attempts), len(baseline_rejected)),
        "unrepaired": _unrepaired_cases(retry_attempts),
        "similarity_delta_distribution": _distribution(deltas),
        "diagnostic_class_breakdown": dict(sorted(breakdown.items())),
        "ledger_commit_rate": _ratio(len(committed), len(retry_attempts)),
        "bundle_sha": None,
        "attestation_sha": None,
    }


def write_batch_proof(path: Path, proof: dict[str, Any]) -> None:
    unsigned = dict(proof)
    unsigned["bundle_sha"] = None
    unsigned["attestation_sha"] = None
    unsigned_bytes = _canonical_bytes(unsigned)
    proof["bundle_sha"] = hashlib.sha256(unsigned_bytes).hexdigest()
    attestation_payload = dict(proof)
    attestation_payload["attestation_sha"] = None
    proof["attestation_sha"] = hashlib.sha256(
        _canonical_bytes(attestation_payload)
    ).hexdigest()
    _write_json(path, proof)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Claude Phase 3 diagnostic retry loop across CUC v5.",
    )
    parser.add_argument("--params-json", type=Path, default=DEFAULT_PARAMS_PATH)
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=SINGLE_CASE_OUTPUT_DIR,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ledger-root", type=Path, default=None)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--proof-dir", type=Path, default=DEFAULT_PROOF_DIR)
    parser.add_argument("--case-filter", action="append", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-date", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--fallback-model", nargs="?", const="", default="")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--effort", default=None)
    parser.add_argument("--strict-copy", action="store_true")
    parser.add_argument("--rate-limit-retries", type=int, default=5)
    parser.add_argument("--rate-limit-sleep-seconds", type=float, default=70.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.model is None:
        from scripts.claude_phase3_diagnostic_retry import (  # noqa: PLC0415
            DEFAULT_CLAUDE_MODEL,
        )

        args.model = DEFAULT_CLAUDE_MODEL
    ledger_root = args.ledger_root or args.output_dir / "ledger"
    run_batch_retry(
        params_json=args.params_json,
        baseline_dir=args.baseline_dir,
        output_dir=args.output_dir,
        ledger_root=ledger_root,
        results_dir=args.results_dir,
        proof_dir=args.proof_dir,
        proposer_args=args,
        case_filters=args.case_filter,
        dry_run=args.dry_run,
        run_date=args.run_date,
    )
    return 0


def _run_or_synthesize_case(
    *,
    spec: BatchCaseSpec,
    baseline_dir: Path,
    output_dir: Path,
    ledger_root: Path,
    proposer_args: argparse.Namespace,
    dry_run: bool,
) -> dict[str, Any]:
    runtime_params_json = _materialize_runtime_case(
        spec=spec,
        output_dir=output_dir,
    )
    if _baseline_model_delta_path(baseline_dir, spec.case_id).is_file():
        return run_diagnostic_retry(
            case_id=spec.case_id,
            params_json=runtime_params_json,
            baseline_dir=baseline_dir,
            output_dir=output_dir,
            ledger_root=ledger_root,
            proposer=build_proposer(proposer_args),
            strict_copy=bool(proposer_args.strict_copy),
            dry_run=dry_run,
        )
    if not dry_run:
        raise FileNotFoundError(
            "baseline model_delta.json missing for "
            f"{spec.case_id}; run a baseline probe first or pass --dry-run"
        )
    return _synthetic_accepted_result(spec)


def _synthetic_accepted_result(spec: BatchCaseSpec) -> dict[str, Any]:
    gap_summary = {
        "compared_fields": 0,
        "matching_fields": 0,
        "similarity_score_percent": 100.0,
    }
    return {
        "schema_version": "iv.cuc_harness.synthetic_dry_run.v1",
        "case_id": spec.case_id,
        "source_case_id": spec.source_case_id,
        "fixture_dir": spec.fixture_dir.as_posix(),
        "dry_run_source": "gold_expected_delta",
        "diagnostic_class": "ACCEPTED",
        "baseline": {
            "accepted": True,
            "reasons": [],
            "reason_families": [],
            "gap_summary": gap_summary,
            "model_delta_path": None,
            "gap_report_path": None,
        },
        "retry": {
            "called": False,
            "reason": "baseline_artifact_missing_dry_run",
            "accepted": None,
            "ledger_committed": False,
            "ledger_commit": None,
        },
    }


def _classify_terminal_retry(retry: Mapping[str, Any]) -> str:
    families = _string_list(retry.get("reason_families"))
    if not families:
        if retry.get("json_valid") is False:
            return "SCHEMA_VIOLATION"
        return "UNCLASSIFIED"
    return classify_failure_family(
        DeltaVerificationResult(
            accepted=False,
            issues=tuple(_issue_from_family(family) for family in families),
        ),
        {},
    )


def _unrepaired_cases(
    retry_attempts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    unrepaired = []
    for result in retry_attempts:
        if result.get("retry_accepted") is not False:
            continue
        unrepaired.append(
            {
                "case_id": result["case_id"],
                "terminal_diagnostic_class": result["terminal_diagnostic_class"],
                "similarity_score": result["retry_similarity"],
                "terminal_failure_reasons": result["terminal_failure_reasons"],
            }
        )
    return unrepaired


def _issue_from_family(family: str):
    from core.cuc_harness.verifier import VerificationIssue  # noqa: PLC0415

    return VerificationIssue(family=family)


def _materialize_runtime_case(
    *,
    spec: BatchCaseSpec,
    output_dir: Path,
) -> Path:
    runtime_root = output_dir / "runtime_fixtures" / _safe_name(spec.case_id)
    runtime_root.mkdir(parents=True, exist_ok=True)
    _write_json(runtime_root / "clean_pack.json", spec.clean_pack)
    _write_json(runtime_root / "perturbed_pack.json", spec.perturbed_pack)
    _write_json(runtime_root / "expected_delta.json", spec.expected_delta)
    params_path = output_dir / "runtime_params" / f"{_safe_name(spec.case_id)}.json"
    params_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        params_path,
        [
            {
                "case_id": spec.case_id,
                "source_fixture_dir": runtime_root.as_posix(),
            }
        ],
    )
    return params_path


def _load_param_records(params_json: Path) -> list[Mapping[str, Any]]:
    records = _read_json(params_json)
    if not isinstance(records, list):
        raise ValueError(f"params file must contain a list: {params_json}")
    return [record for record in records if isinstance(record, Mapping)]


def _case_spec_from_record(record: Mapping[str, Any]) -> BatchCaseSpec:
    case_id = str(record["case_id"])
    source_fixture_dir = Path(str(record.get("source_fixture_dir", "")))
    fixture_dir = (
        source_fixture_dir
        if source_fixture_dir.is_absolute()
        else REPO_ROOT / source_fixture_dir
    )
    return BatchCaseSpec(
        case_id=case_id,
        source_case_id=str(record.get("source_case_id", fixture_dir.name)),
        fixture_dir=fixture_dir,
        clean_pack=_required_mapping(record, "clean_pack_json"),
        perturbed_pack=_required_mapping(record, "perturbed_pack_json"),
        expected_delta=_required_mapping(record, "expected_delta_json"),
    )


def _required_mapping(record: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{record.get('case_id', '<unknown>')} missing {key}")
    return value


def _baseline_model_delta_path(baseline_dir: Path, case_id: str) -> Path:
    safe_case_id = _safe_name(case_id)
    candidates = [
        baseline_dir / "model_delta.json",
        baseline_dir / case_id / "model_delta.json",
        baseline_dir / safe_case_id / "model_delta.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[-1]


def _summary_similarity(value: Any) -> float | None:
    summary = _mapping(value)
    raw = summary.get("similarity_score_percent")
    return float(raw) if isinstance(raw, int | float) else None


def _distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(values),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "mean": round(sum(values) / len(values), 6),
        "median": round(float(statistics.median(values)), 6),
    }


def _count_rate(count: int, denominator: int) -> dict[str, float | int]:
    return {"count": count, "rate": _ratio(count, denominator)}


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y_%m_%d")


if __name__ == "__main__":
    raise SystemExit(main())
