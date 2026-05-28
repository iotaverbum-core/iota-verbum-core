from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts.deepseek_cuc_smoke_matrix import CaseSpec, run_case  # noqa: E402

from core.cuc_harness.claude_proposer import (  # noqa: E402
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_CLAUDE_RATE_LIMIT_RETRIES,
    DEFAULT_CLAUDE_RATE_LIMIT_SLEEP_SECONDS,
    ClaudeProposer,
)

DEFAULT_PARAMS_PATH = REPO_ROOT / "benchmark" / "cuc_v4_candidate_params.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cuc-results" / "claude_24_production_probe" / "latest"
SCHEMA_VERSION = "iv.cuc_harness.claude_24_production_probe.v1"
EXPECTED_CASE_COUNT = 24


def load_case_specs(
    params_path: Path = DEFAULT_PARAMS_PATH,
    case_ids: list[str] | None = None,
    limit: int | None = None,
) -> list[CaseSpec]:
    params = json.loads(params_path.read_text(encoding="utf-8"))
    if not isinstance(params, list):
        raise ValueError(f"params file must contain a list: {params_path}")
    by_id = {str(item["case_id"]): item for item in params}
    requested_ids = case_ids or [str(item["case_id"]) for item in params]
    missing = [case_id for case_id in requested_ids if case_id not in by_id]
    if missing:
        raise ValueError(f"case_id not found in {params_path}: {', '.join(missing)}")
    if limit is not None:
        requested_ids = requested_ids[:limit]

    specs: list[CaseSpec] = []
    for case_id in requested_ids:
        item = by_id[case_id]
        fixture_dir = _resolve_repo_path(Path(str(item["source_fixture_dir"])))
        _require_fixture_file(fixture_dir / "clean_pack.json")
        _require_fixture_file(fixture_dir / "perturbed_pack.json")
        _require_fixture_file(fixture_dir / "expected_delta.json")
        specs.append(
            CaseSpec(
                case_id=case_id,
                source_case_id=fixture_dir.name,
                fixture_dir=fixture_dir,
            )
        )
    return specs


def run_production_matrix(
    *,
    specs: list[CaseSpec],
    proposer: Any,
    output_dir: Path,
    ledger_root: Path,
    strict_copy: bool,
    params_path: Path = DEFAULT_PARAMS_PATH,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_root.mkdir(parents=True, exist_ok=True)
    results = []
    aborted_reason = None
    for spec in specs:
        result = run_case(
            spec=spec,
            proposer=proposer,
            output_dir=output_dir,
            strict_copy=strict_copy,
            ledger_root=ledger_root,
        )
        results.append(result)
        if _is_auth_failure(result):
            aborted_reason = "authentication_failed"
            break

    valid = [result for result in results if result["json_valid"]]
    accepted = [result for result in results if result["verifier_accepted"]]
    committed = [result for result in results if result["ledger_committed"]]
    summary = {
        "requested_case_count": len(specs),
        "case_count": len(results),
        "json_valid_count": len(valid),
        "verifier_accepted_count": len(accepted),
        "ledger_committed_count": len(committed),
        "json_valid_rate": _ratio(len(valid), len(results)),
        "acceptance_rate": _ratio(len(accepted), len(results)),
        "ledger_commit_rate": _ratio(len(committed), len(results)),
        "average_similarity_score_percent": _average(
            [
                result["gap_summary"]["similarity_score_percent"]
                for result in results
                if result.get("gap_summary")
            ]
        ),
    }
    if aborted_reason is not None:
        summary["aborted_reason"] = aborted_reason

    payload = {
        "schema_version": SCHEMA_VERSION,
        "params_path": params_path.as_posix(),
        "model": proposer.model,
        "fallback_model": proposer.fallback_model,
        "max_tokens": getattr(proposer, "max_tokens", None),
        "rate_limit_retries": getattr(proposer, "rate_limit_retries", None),
        "rate_limit_sleep_seconds": getattr(proposer, "rate_limit_sleep_seconds", None),
        "output_dir": output_dir.as_posix(),
        "ledger_root": ledger_root.as_posix(),
        "case_ids": [spec.case_id for spec in specs],
        "summary": summary,
        "results": results,
    }
    if getattr(proposer, "effort", None):
        payload["effort"] = proposer.effort
    _write_json(output_dir / "summary.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return payload


def build_proposer(args: argparse.Namespace) -> ClaudeProposer:
    return ClaudeProposer(
        model=args.model,
        fallback_model=args.fallback_model,
        timeout_seconds=args.timeout_seconds,
        max_tokens=args.max_tokens,
        effort=args.effort,
        rate_limit_retries=args.rate_limit_retries,
        rate_limit_sleep_seconds=args.rate_limit_sleep_seconds,
    )


def build_dry_run_payload(
    *,
    specs: list[CaseSpec],
    params_path: Path,
    output_dir: Path,
    ledger_root: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "params_path": params_path.as_posix(),
        "output_dir": output_dir.as_posix(),
        "ledger_root": ledger_root.as_posix(),
        "case_count": len(specs),
        "case_ids": [spec.case_id for spec in specs],
    }


def default_ledger_root(output_dir: Path) -> Path:
    return output_dir / "ledger"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the 24-case Claude CUC production probe with ledger sealing.",
    )
    parser.add_argument("--params-json", type=Path, default=DEFAULT_PARAMS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--ledger-root",
        type=Path,
        default=None,
        help="Ledger root. Defaults to <output-dir>/ledger.",
    )
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--model",
        default=os.getenv("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL),
    )
    parser.add_argument(
        "--fallback-model",
        nargs="?",
        const="",
        default=os.getenv("CLAUDE_FALLBACK_MODEL", ""),
    )
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--effort", default=os.getenv("CLAUDE_EFFORT"))
    parser.add_argument("--strict-copy", action="store_true")
    parser.add_argument(
        "--rate-limit-retries",
        type=int,
        default=DEFAULT_CLAUDE_RATE_LIMIT_RETRIES,
        help="Number of HTTP 429 retries before recording a case error.",
    )
    parser.add_argument(
        "--rate-limit-sleep-seconds",
        type=float,
        default=DEFAULT_CLAUDE_RATE_LIMIT_SLEEP_SECONDS,
        help="Fallback sleep duration for HTTP 429 retries when Retry-After is absent.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    specs = load_case_specs(args.params_json, args.case_id, args.limit)
    ledger_root = args.ledger_root or default_ledger_root(args.output_dir)
    if args.dry_run:
        payload = build_dry_run_payload(
            specs=specs,
            params_path=args.params_json,
            output_dir=args.output_dir,
            ledger_root=ledger_root,
        )
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    proposer = build_proposer(args)
    run_production_matrix(
        specs=specs,
        proposer=proposer,
        output_dir=args.output_dir,
        ledger_root=ledger_root,
        strict_copy=args.strict_copy,
        params_path=args.params_json,
    )
    return 0


def _require_fixture_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"required fixture file not found: {path.as_posix()}")


def _resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _is_auth_failure(result: dict[str, Any]) -> bool:
    failure = result.get("failure")
    if not isinstance(failure, dict):
        return False
    if failure.get("status_code") == 401:
        return True
    response_body = failure.get("response_body")
    if not isinstance(response_body, dict):
        return False
    error = response_body.get("error")
    return isinstance(error, dict) and error.get("type") == "authentication_error"


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


if __name__ == "__main__":
    raise SystemExit(main())
