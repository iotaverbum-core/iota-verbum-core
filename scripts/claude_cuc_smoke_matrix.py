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

from scripts.deepseek_cuc_smoke_matrix import (  # noqa: E402
    DEFAULT_PARAMS_PATH,
    CaseSpec,
    load_case_specs,
    run_case,
)

DEFAULT_OUTPUT_DIR = REPO_ROOT / "cuc-results" / "claude_smoke_matrix" / "latest"


def run_smoke_matrix(
    *,
    specs: list[CaseSpec],
    proposer: Any,
    output_dir: Path,
    strict_copy: bool,
    ledger_root: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
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
    accepted = [result for result in results if result["verifier_accepted"]]
    valid = [result for result in results if result["json_valid"]]
    committed = [result for result in results if result["ledger_committed"]]
    summary = {
        "requested_case_count": len(specs),
        "case_count": len(results),
        "json_valid_count": len(valid),
        "verifier_accepted_count": len(accepted),
        "ledger_committed_count": len(committed),
        "acceptance_rate": _ratio(len(accepted), len(results)),
        "json_valid_rate": _ratio(len(valid), len(results)),
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
        "schema_version": "iv.cuc_harness.claude_smoke_matrix.v1",
        "model": proposer.model,
        "fallback_model": proposer.fallback_model,
        "case_ids": [spec.case_id for spec in specs],
        "summary": summary,
        "results": results,
    }
    if getattr(proposer, "effort", None):
        payload["effort"] = proposer.effort
    if getattr(proposer, "max_tokens", None):
        payload["max_tokens"] = proposer.max_tokens
    _write_json(output_dir / "summary.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return payload


def build_proposer(args: argparse.Namespace) -> Any:
    from core.cuc_harness.claude_proposer import ClaudeProposer

    return ClaudeProposer(
        model=args.model,
        fallback_model=args.fallback_model,
        timeout_seconds=args.timeout_seconds,
        max_tokens=args.max_tokens,
        effort=args.effort,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a 5-case Claude CUC proposer smoke matrix.",
    )
    parser.add_argument("--params-json", type=Path, default=DEFAULT_PARAMS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument(
        "--model",
        default=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
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
        "--ledger-root",
        type=Path,
        default=None,
        help="Optional ledger root. Accepted deltas are sealed and committed here.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    specs = load_case_specs(args.params_json, args.case_id)
    proposer = build_proposer(args)
    run_smoke_matrix(
        specs=specs,
        proposer=proposer,
        output_dir=args.output_dir,
        strict_copy=args.strict_copy,
        ledger_root=args.ledger_root,
    )
    return 0


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
