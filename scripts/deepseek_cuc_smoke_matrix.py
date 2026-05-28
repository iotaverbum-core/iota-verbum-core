from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

DEFAULT_PARAMS_PATH = REPO_ROOT / "benchmark" / "cuc_v5a_candidate_params.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cuc-results" / "deepseek_smoke_matrix" / "latest"
DEFAULT_CASE_IDS = [
    "CUCV5A-PRESERVE-02-SIBLING-STABILITY-SECURITY-INCIDENT",
    "CUCV5A-NOOP-02-OPERATIONS-BRIEF",
    "CUCV5A-GROUNDING-01-SOURCE-RELIABILITY-COLLAPSE-PROCUREMENT-REVIEW",
    "CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT",
    "CUCV5A-CORE-07-DEFERRED-EFFECT-LEGAL-CONTRACT",
]


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    source_case_id: str
    fixture_dir: Path


def load_case_specs(
    params_path: Path = DEFAULT_PARAMS_PATH,
    case_ids: list[str] | None = None,
) -> list[CaseSpec]:
    params = json.loads(params_path.read_text(encoding="utf-8"))
    requested_ids = case_ids or DEFAULT_CASE_IDS
    by_id = {item["case_id"]: item for item in params}
    specs: list[CaseSpec] = []
    for case_id in requested_ids:
        try:
            item = by_id[case_id]
        except KeyError as exc:
            raise ValueError(f"case_id not found in {params_path}: {case_id}") from exc
        fixture_dir = _resolve_repo_path(Path(item["source_fixture_dir"]))
        _require_fixture_file(fixture_dir / "clean_pack.json")
        _require_fixture_file(fixture_dir / "perturbed_pack.json")
        _require_fixture_file(fixture_dir / "expected_delta.json")
        specs.append(
            CaseSpec(
                case_id=case_id,
                source_case_id=str(item["source_case_id"]),
                fixture_dir=fixture_dir,
            )
        )
    return specs


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
        "schema_version": "iv.cuc_harness.deepseek_smoke_matrix.v1",
        "model": proposer.model,
        "fallback_model": proposer.fallback_model,
        "case_ids": [spec.case_id for spec in specs],
        "summary": summary,
        "results": results,
    }
    _write_json(output_dir / "summary.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return payload


def run_case(
    *,
    spec: CaseSpec,
    proposer: Any,
    output_dir: Path,
    strict_copy: bool,
    ledger_root: Path | None = None,
) -> dict[str, Any]:
    from scripts.delta_gap_diagnostic import compare_deltas

    from core.cuc_harness.deepseek_proposer import RevisionDelta, SealedFailureArtifact
    from core.cuc_harness.ledger_commit import commit_verified_revision_delta
    from core.cuc_harness.verifier import verify_revision_delta
    from core.determinism.canonical_json import dumps_canonical

    clean_pack = _read_json(spec.fixture_dir / "clean_pack.json")
    perturbed_pack = _read_json(spec.fixture_dir / "perturbed_pack.json")
    gold_delta = _read_json(spec.fixture_dir / "expected_delta.json")
    proposal = proposer.propose(
        clean_pack,
        perturbed_pack,
        case_id=spec.case_id,
        strict_copy=strict_copy,
    )
    case_output_dir = output_dir / _safe_name(spec.case_id)
    case_output_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "case_id": spec.case_id,
        "source_case_id": spec.source_case_id,
        "fixture_dir": spec.fixture_dir.as_posix(),
        "json_valid": isinstance(proposal, RevisionDelta),
        "verifier_accepted": False,
        "verifier_reasons": [],
        "gap_summary": None,
        "model_delta_path": None,
        "gap_report_path": None,
        "ledger_committed": False,
        "ledger_commit": None,
    }
    if isinstance(proposal, SealedFailureArtifact):
        result["verifier_reasons"] = [proposal.error_type]
        failure_payload = proposal.model_dump(mode="json")
        result["failure"] = {
            "error_type": proposal.error_type,
            "message": proposal.message,
            "status_code": proposal.status_code,
            "response_body": proposal.response_body,
        }
        _write_json(case_output_dir / "failure.json", failure_payload)
        return result

    delta_payload = proposal.model_dump(mode="json")
    delta_path = case_output_dir / "model_delta.json"
    delta_path.write_bytes(dumps_canonical(delta_payload))
    verification = verify_revision_delta(
        proposal,
        gold_delta,
    )
    gap_report = compare_deltas(delta_payload, gold_delta).to_dict()
    gap_report_path = case_output_dir / "gap_report.json"
    _write_json(gap_report_path, gap_report)
    ledger_commit = None
    if verification.accepted and ledger_root is not None:
        commit_result = commit_verified_revision_delta(
            case_id=spec.case_id,
            model=proposer.model,
            clean_pack=clean_pack,
            perturbed_pack=perturbed_pack,
            expected_delta=gold_delta,
            delta=proposal,
            verification=verification,
            ledger_root=ledger_root,
        )
        ledger_commit = commit_result.to_dict()

    result.update(
        {
            "verifier_accepted": verification.accepted,
            "verifier_reasons": verification.reasons,
            "verifier_reason_families": verification.reason_families,
            "gap_summary": gap_report["summary"],
            "model_delta_path": delta_path.as_posix(),
            "gap_report_path": gap_report_path.as_posix(),
            "ledger_committed": ledger_commit is not None,
            "ledger_commit": ledger_commit,
        }
    )
    return result


def verify_delta_against_gold(
    proposal: Any,
    gold_delta: dict[str, Any],
) -> tuple[bool, list[str]]:
    from core.cuc_harness.verifier import verify_revision_delta

    verification = verify_revision_delta(proposal, gold_delta)
    return verification.accepted, verification.reasons


def build_proposer(args: argparse.Namespace) -> Any:
    from core.cuc_harness.deepseek_proposer import DeepSeekProposer

    return DeepSeekProposer(
        model=args.model,
        fallback_model=args.fallback_model,
        timeout_seconds=args.timeout_seconds,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a 5-case DeepSeek CUC proposer smoke matrix.",
    )
    parser.add_argument("--params-json", type=Path, default=DEFAULT_PARAMS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument(
        "--model",
        default=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    )
    parser.add_argument(
        "--fallback-model",
        nargs="?",
        const="",
        default=os.getenv("DEEPSEEK_FALLBACK_MODEL", ""),
    )
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
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


def _require_fixture_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"required fixture file not found: {path.as_posix()}")


def _resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


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
