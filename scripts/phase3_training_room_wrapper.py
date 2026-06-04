from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.cuc_harness.claude_proposer import (  # noqa: E402
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_CLAUDE_RATE_LIMIT_RETRIES,
    DEFAULT_CLAUDE_RATE_LIMIT_SLEEP_SECONDS,
    ClaudeProposer,
)
from core.cuc_harness.deepseek_proposer import (  # noqa: E402
    DEFAULT_DEEPSEEK_MODEL,
    DeepSeekProposer,
    RevisionDelta,
)
from core.cuc_harness.verifier import (  # noqa: E402
    DeltaVerificationResult,
    verify_revision_delta,
)
from scripts.claude_phase3_diagnostic_retry import (  # noqa: E402
    _load_or_compare_gap_report,
    _safe_name,
    resolve_baseline_case_dir,
    run_diagnostic_retry as run_claude_diagnostic_retry,
)
from scripts.deepseek_phase3_diagnostic_retry import (  # noqa: E402
    run_diagnostic_retry as run_deepseek_diagnostic_retry,
)

SCHEMA_VERSION = "iv.phase3.training_room_wrapper.v1"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cuc-results" / "phase3_training_room"


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    source_case_id: str
    fixture_dir: Path


@dataclass(frozen=True)
class TrainingRoomRequest:
    provider: Literal["claude", "deepseek"]
    case_id: str
    params_json: Path
    baseline_dir: Path
    output_dir: Path = DEFAULT_OUTPUT_DIR
    ledger_root: Path | None = None
    training_dirs: tuple[Path, ...] = ()
    max_training_passes: int = 0
    allow_live_model: bool = False
    strict_copy: bool = False
    model: str | None = None
    fallback_model: str = ""
    timeout_seconds: float = 90.0
    max_tokens: int = 8192
    effort: str | None = None
    rate_limit_retries: int = DEFAULT_CLAUDE_RATE_LIMIT_RETRIES
    rate_limit_sleep_seconds: float = DEFAULT_CLAUDE_RATE_LIMIT_SLEEP_SECONDS


def run_training_room_session(request: TrainingRoomRequest) -> dict[str, Any]:
    spec = load_case_spec(request.params_json, request.case_id)
    expected_delta = _read_json(spec.fixture_dir / "expected_delta.json")
    output_dir = request.output_dir
    case_output_dir = output_dir / _safe_name(request.case_id)
    case_output_dir.mkdir(parents=True, exist_ok=True)
    ledger_root = request.ledger_root or output_dir / "ledger"

    baseline = load_baseline_candidate(
        case_id=request.case_id,
        baseline_dir=request.baseline_dir,
        expected_delta=expected_delta,
    )
    pass_results = [
        normalize_training_summary(path)
        for path in _training_summary_paths(
            request.training_dirs,
            request.case_id,
        )
    ]

    current_baseline_dir = request.baseline_dir
    stop_reason = "no_training_requested"
    if baseline["accepted"]:
        stop_reason = "baseline_accepted"
    elif request.max_training_passes > 0 and not request.allow_live_model:
        pass_result = run_training_pass(
            request=request,
            pass_index=1,
            baseline_dir=current_baseline_dir,
            output_dir=output_dir / "passes" / "pass_001",
            ledger_root=ledger_root,
            dry_run=True,
        )
        pass_results.append(pass_result)
        stop_reason = "live_model_not_enabled"
    elif request.max_training_passes > 0:
        stop_reason = "budget_exhausted"
        for pass_index in range(1, request.max_training_passes + 1):
            pass_result = run_training_pass(
                request=request,
                pass_index=pass_index,
                baseline_dir=current_baseline_dir,
                output_dir=output_dir / "passes" / f"pass_{pass_index:03d}",
                ledger_root=ledger_root,
                dry_run=False,
            )
            pass_results.append(pass_result)
            guard = _mapping(pass_result.get("no_regression_guard"))
            current_baseline_dir = Path(
                str(guard.get("next_baseline_dir") or current_baseline_dir)
            )
            if _candidate_from_pass(pass_result)["accepted"]:
                stop_reason = "accepted"
                break
            if guard.get("retry_regressed") is True:
                stop_reason = "no_improvement"
                break

    scorecard = build_scorecard(
        provider=request.provider,
        spec=spec,
        baseline=baseline,
        pass_results=pass_results,
        output_dir=output_dir,
        ledger_root=ledger_root,
        stop_reason=stop_reason,
        allow_live_model=request.allow_live_model,
    )
    scorecard_path = case_output_dir / "scorecard.json"
    _write_json(scorecard_path, scorecard)
    scorecard["artifacts"]["scorecard_path"] = scorecard_path.as_posix()
    _write_json(scorecard_path, scorecard)
    print(json.dumps(scorecard, indent=2, sort_keys=True, ensure_ascii=True))
    return scorecard


def load_case_spec(params_json: Path, case_id: str) -> CaseSpec:
    records = _read_json(params_json)
    if not isinstance(records, list):
        raise ValueError(f"params_json must contain a list: {params_json}")
    for record in records:
        if not isinstance(record, Mapping) or str(record.get("case_id")) != case_id:
            continue
        fixture_dir = _resolve_path(Path(str(record["source_fixture_dir"])))
        return CaseSpec(
            case_id=case_id,
            source_case_id=str(record.get("source_case_id") or fixture_dir.name),
            fixture_dir=fixture_dir,
        )
    raise ValueError(f"case_id not found in {params_json}: {case_id}")


def load_baseline_candidate(
    *,
    case_id: str,
    baseline_dir: Path,
    expected_delta: Mapping[str, Any],
) -> dict[str, Any]:
    baseline_case_dir = resolve_baseline_case_dir(baseline_dir, case_id)
    baseline_delta_path = baseline_case_dir / "model_delta.json"
    baseline_delta = _read_json(baseline_delta_path)
    proposal = RevisionDelta.model_validate(baseline_delta)
    verification = verify_revision_delta(proposal, expected_delta)
    gap_report = _load_or_compare_gap_report(
        baseline_case_dir,
        baseline_delta,
        expected_delta,
    )
    gap_path = baseline_case_dir / "gap_report.json"
    return _candidate_summary(
        label="baseline",
        verification=verification,
        gap_report=gap_report,
        model_delta_path=baseline_delta_path,
        gap_report_path=gap_path if gap_path.is_file() else None,
        ledger_commit=None,
    )


def run_training_pass(
    *,
    request: TrainingRoomRequest,
    pass_index: int,
    baseline_dir: Path,
    output_dir: Path,
    ledger_root: Path,
    dry_run: bool,
) -> dict[str, Any]:
    if request.provider == "claude":
        result = run_claude_diagnostic_retry(
            case_id=request.case_id,
            params_json=request.params_json,
            baseline_dir=baseline_dir,
            output_dir=output_dir,
            ledger_root=ledger_root,
            proposer=ClaudeProposer(
                model=request.model or DEFAULT_CLAUDE_MODEL,
                fallback_model=request.fallback_model,
                timeout_seconds=request.timeout_seconds,
                max_tokens=request.max_tokens,
                effort=request.effort,
                rate_limit_retries=request.rate_limit_retries,
                rate_limit_sleep_seconds=request.rate_limit_sleep_seconds,
            ),
            strict_copy=request.strict_copy,
            dry_run=dry_run,
        )
    else:
        result = run_deepseek_diagnostic_retry(
            case_id=request.case_id,
            params_json=request.params_json,
            baseline_dir=baseline_dir,
            output_dir=output_dir,
            ledger_root=ledger_root,
            proposer=DeepSeekProposer(
                model=request.model or DEFAULT_DEEPSEEK_MODEL,
                fallback_model=request.fallback_model,
                timeout_seconds=request.timeout_seconds,
            ),
            strict_copy=request.strict_copy,
            dry_run=dry_run,
        )
    result["training_pass_index"] = pass_index
    return result


def normalize_training_summary(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"training summary must be an object: {path}")
    payload = dict(payload)
    payload["training_summary_path"] = path.as_posix()
    return payload


def build_scorecard(
    *,
    provider: str,
    spec: CaseSpec,
    baseline: Mapping[str, Any],
    pass_results: Sequence[Mapping[str, Any]],
    output_dir: Path,
    ledger_root: Path,
    stop_reason: str,
    allow_live_model: bool,
) -> dict[str, Any]:
    pass_summaries = [
        _pass_scorecard(pass_index=index + 1, pass_result=pass_result)
        for index, pass_result in enumerate(pass_results)
    ]
    candidates = [baseline, *(_candidate_from_pass(item) for item in pass_results)]
    best = max(candidates, key=_candidate_rank)
    training_effect = {
        "accepted_before": bool(baseline["accepted"]),
        "accepted_after": bool(best["accepted"]),
        "similarity_before": baseline["similarity_score_percent"],
        "similarity_after": best["similarity_score_percent"],
        "similarity_delta": round(
            float(best["similarity_score_percent"])
            - float(baseline["similarity_score_percent"]),
            6,
        ),
        "verifier_reason_count_before": baseline["verifier_reason_count"],
        "verifier_reason_count_after": best["verifier_reason_count"],
        "improved": _candidate_rank(best) > _candidate_rank(baseline),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "service_kind": "iota_training_room",
        "provider": provider,
        "case_id": spec.case_id,
        "source_case_id": spec.source_case_id,
        "allow_live_model": allow_live_model,
        "stop_reason": stop_reason,
        "baseline": dict(baseline),
        "training_passes": pass_summaries,
        "best_candidate": dict(best),
        "training_effect": training_effect,
        "artifacts": {
            "output_dir": output_dir.as_posix(),
            "ledger_root": ledger_root.as_posix(),
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or score an Iota Phase 3 paid training-room session.",
    )
    parser.add_argument("--provider", choices=["claude", "deepseek"], required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--params-json", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ledger-root", type=Path, default=None)
    parser.add_argument("--training-dir", action="append", type=Path, default=[])
    parser.add_argument("--max-training-passes", type=int, default=0)
    parser.add_argument("--allow-live-model", action="store_true")
    parser.add_argument("--strict-copy", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--fallback-model", nargs="?", const="", default="")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--effort", default=None)
    parser.add_argument("--rate-limit-retries", type=int, default=5)
    parser.add_argument("--rate-limit-sleep-seconds", type=float, default=70.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    run_training_room_session(
        TrainingRoomRequest(
            provider=args.provider,
            case_id=args.case_id,
            params_json=args.params_json,
            baseline_dir=args.baseline_dir,
            output_dir=args.output_dir,
            ledger_root=args.ledger_root,
            training_dirs=tuple(args.training_dir),
            max_training_passes=args.max_training_passes,
            allow_live_model=args.allow_live_model,
            strict_copy=args.strict_copy,
            model=args.model,
            fallback_model=args.fallback_model,
            timeout_seconds=args.timeout_seconds,
            max_tokens=args.max_tokens,
            effort=args.effort,
            rate_limit_retries=args.rate_limit_retries,
            rate_limit_sleep_seconds=args.rate_limit_sleep_seconds,
        )
    )
    return 0


def _candidate_summary(
    *,
    label: str,
    verification: DeltaVerificationResult,
    gap_report: Mapping[str, Any],
    model_delta_path: Path | None,
    gap_report_path: Path | None,
    ledger_commit: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "label": label,
        "accepted": verification.accepted,
        "similarity_score_percent": _similarity_score(gap_report),
        "verifier_reason_count": len(verification.reasons),
        "verifier_reasons": verification.reasons,
        "verifier_reason_families": verification.reason_families,
        "model_delta_path": model_delta_path.as_posix() if model_delta_path else None,
        "gap_report_path": gap_report_path.as_posix() if gap_report_path else None,
        "ledger_committed": ledger_commit is not None,
        "ledger_commit": dict(ledger_commit) if ledger_commit else None,
    }


def _candidate_from_pass(pass_result: Mapping[str, Any]) -> dict[str, Any]:
    retry = _mapping(pass_result.get("retry"))
    if not bool(retry.get("called", False)):
        baseline = _mapping(pass_result.get("baseline"))
        return _candidate_from_summary("pass_baseline", baseline)
    return {
        "label": "retry",
        "accepted": bool(retry.get("accepted", False)),
        "similarity_score_percent": _summary_similarity(retry.get("gap_summary")),
        "verifier_reason_count": len(_string_list(retry.get("reasons"))),
        "verifier_reasons": _string_list(retry.get("reasons")),
        "verifier_reason_families": _string_list(retry.get("reason_families")),
        "model_delta_path": retry.get("model_delta_path"),
        "gap_report_path": retry.get("gap_report_path"),
        "ledger_committed": bool(retry.get("ledger_committed", False)),
        "ledger_commit": retry.get("ledger_commit"),
    }


def _candidate_from_summary(label: str, summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "accepted": bool(summary.get("accepted", False)),
        "similarity_score_percent": _summary_similarity(summary.get("gap_summary")),
        "verifier_reason_count": len(_string_list(summary.get("reasons"))),
        "verifier_reasons": _string_list(summary.get("reasons")),
        "verifier_reason_families": _string_list(summary.get("reason_families")),
        "model_delta_path": summary.get("model_delta_path"),
        "gap_report_path": summary.get("gap_report_path"),
        "ledger_committed": False,
        "ledger_commit": None,
    }


def _pass_scorecard(
    *,
    pass_index: int,
    pass_result: Mapping[str, Any],
) -> dict[str, Any]:
    retry = _mapping(pass_result.get("retry"))
    guard = _mapping(pass_result.get("no_regression_guard"))
    training_effect = _mapping(pass_result.get("training_effect"))
    candidate = _candidate_from_pass(pass_result)
    return {
        "pass_index": int(pass_result.get("training_pass_index", pass_index)),
        "called": bool(retry.get("called", False)),
        "accepted": candidate["accepted"],
        "similarity_score_percent": candidate["similarity_score_percent"],
        "verifier_reason_count": candidate["verifier_reason_count"],
        "ledger_committed": candidate["ledger_committed"],
        "selected_candidate": guard.get("selected_candidate"),
        "retry_regressed": guard.get("retry_regressed"),
        "training_effect": dict(training_effect),
        "training_summary_path": pass_result.get("training_summary_path"),
    }


def _candidate_rank(candidate: Mapping[str, Any]) -> tuple[int, float, int]:
    return (
        int(bool(candidate.get("accepted", False))),
        float(candidate.get("similarity_score_percent") or 0.0),
        -int(candidate.get("verifier_reason_count") or 0),
    )


def _training_summary_paths(
    training_dirs: Sequence[Path],
    case_id: str,
) -> list[Path]:
    paths: list[Path] = []
    for training_dir in training_dirs:
        for candidate in (
            training_dir / "training_summary.json",
            training_dir / case_id / "training_summary.json",
            training_dir / _safe_name(case_id) / "training_summary.json",
        ):
            if candidate.is_file():
                paths.append(candidate)
                break
        else:
            raise FileNotFoundError(
                "training_summary.json missing under "
                f"{training_dir.as_posix()} for {case_id}"
            )
    return paths


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    for root in (Path.cwd(), REPO_ROOT):
        candidate = root / path
        if candidate.exists():
            return candidate
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _similarity_score(gap_report: Mapping[str, Any]) -> float:
    return _summary_similarity(gap_report.get("summary"))


def _summary_similarity(value: Any) -> float:
    summary = _mapping(value)
    raw = summary.get("similarity_score_percent")
    return float(raw) if isinstance(raw, int | float) else 0.0


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
