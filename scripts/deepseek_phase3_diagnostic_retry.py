from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scripts.claude_phase3_diagnostic_retry import (  # noqa: E402
    _clear_attempt_artifacts,
    _json_block,
    _load_or_compare_gap_report,
    _read_json,
    _safe_name,
    _write_json,
    build_repair_instruction,
    resolve_baseline_case_dir,
    summarize_training_effect,
    write_best_candidate_artifacts,
)
from scripts.deepseek_cuc_smoke_matrix import (  # noqa: E402
    DEFAULT_PARAMS_PATH,
    load_case_specs,
)
from scripts.delta_gap_diagnostic import compare_deltas  # noqa: E402

from core.cuc_harness.deepseek_proposer import (  # noqa: E402
    DEFAULT_DEEPSEEK_MODEL,
    DeepSeekProposer,
    RevisionDelta,
    SealedFailureArtifact,
)
from core.cuc_harness.ledger_commit import commit_verified_revision_delta  # noqa: E402
from core.cuc_harness.verifier import verify_revision_delta  # noqa: E402
from core.determinism.canonical_json import dumps_canonical  # noqa: E402

DEFAULT_CASE_ID = "CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
DEFAULT_BASELINE_DIR = REPO_ROOT / "cuc-results" / "deepseek_v4_live_single_case"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cuc-results" / "deepseek_v4_diagnostic_retry"
SCHEMA_VERSION = "iv.cuc_harness.deepseek_phase3_diagnostic_retry.v1"


@dataclass(frozen=True)
class RetryDeltaResult:
    delta: RevisionDelta
    model: str


def run_diagnostic_retry(
    *,
    case_id: str,
    params_json: Path,
    baseline_dir: Path,
    output_dir: Path,
    ledger_root: Path,
    proposer: DeepSeekProposer,
    strict_copy: bool,
    dry_run: bool,
) -> dict[str, Any]:
    spec = load_case_specs(params_json, [case_id])[0]
    clean_pack = _read_json(spec.fixture_dir / "clean_pack.json")
    perturbed_pack = _read_json(spec.fixture_dir / "perturbed_pack.json")
    gold_delta = _read_json(spec.fixture_dir / "expected_delta.json")

    baseline_case_dir = resolve_baseline_case_dir(baseline_dir, case_id)
    baseline_delta = _read_json(baseline_case_dir / "model_delta.json")
    baseline_proposal = RevisionDelta.model_validate(baseline_delta)
    baseline_verification = verify_revision_delta(baseline_proposal, gold_delta)
    baseline_gap = _load_or_compare_gap_report(
        baseline_case_dir,
        baseline_delta,
        gold_delta,
    )

    case_output_dir = output_dir / _safe_name(case_id)
    case_output_dir.mkdir(parents=True, exist_ok=True)
    ledger_root.mkdir(parents=True, exist_ok=True)
    _clear_attempt_artifacts(case_output_dir)

    _write_json(case_output_dir / "baseline_model_delta.json", baseline_delta)
    _write_json(case_output_dir / "baseline_gap_report.json", baseline_gap)
    _write_json(
        case_output_dir / "baseline_verification.json",
        baseline_verification.to_dict(),
    )

    repair_instruction = build_repair_instruction(
        case_id=case_id,
        verification=baseline_verification,
        gap_report=baseline_gap,
        expected_delta=gold_delta,
    )
    _write_json(case_output_dir / "repair_instruction.json", repair_instruction)

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "source_case_id": spec.source_case_id,
        "fixture_dir": spec.fixture_dir.as_posix(),
        "model": proposer.model,
        "fallback_model": proposer.fallback_model,
        "baseline": {
            "accepted": baseline_verification.accepted,
            "reasons": baseline_verification.reasons,
            "reason_families": baseline_verification.reason_families,
            "gap_summary": baseline_gap["summary"],
            "model_delta_path": (baseline_case_dir / "model_delta.json").as_posix(),
            "gap_report_path": (baseline_case_dir / "gap_report.json").as_posix(),
        },
        "repair_instruction_path": (
            case_output_dir / "repair_instruction.json"
        ).as_posix(),
        "output_dir": output_dir.as_posix(),
        "ledger_root": ledger_root.as_posix(),
    }
    if dry_run:
        result["retry"] = {"called": False, "reason": "dry_run"}
        result["no_regression_guard"] = write_best_candidate_artifacts(
            case_output_dir=case_output_dir,
            baseline_delta=baseline_delta,
            baseline_verification=baseline_verification,
            baseline_gap=baseline_gap,
        )
        _write_json(case_output_dir / "training_summary.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return result

    retry_messages = build_retry_messages(
        proposer=proposer,
        clean_pack=clean_pack,
        perturbed_pack=perturbed_pack,
        case_id=case_id,
        strict_copy=strict_copy,
        baseline_delta=baseline_delta,
        baseline_verification=baseline_verification.to_dict(),
        baseline_gap=baseline_gap,
        repair_instruction=repair_instruction,
    )
    retry_result = request_retry_delta(proposer, retry_messages)
    if isinstance(retry_result, SealedFailureArtifact):
        failure_path = case_output_dir / "retry_failure.json"
        _write_json(failure_path, retry_result.model_dump(mode="json"))
        result["retry"] = {
            "called": True,
            "json_valid": False,
            "accepted": False,
            "failure_path": failure_path.as_posix(),
            "failure": retry_result.model_dump(mode="json"),
        }
        result["no_regression_guard"] = write_best_candidate_artifacts(
            case_output_dir=case_output_dir,
            baseline_delta=baseline_delta,
            baseline_verification=baseline_verification,
            baseline_gap=baseline_gap,
        )
        _write_json(case_output_dir / "training_summary.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return result

    retry_proposal = retry_result.delta
    retry_model = retry_result.model
    retry_delta = retry_proposal.model_dump(mode="json")
    retry_delta_path = case_output_dir / "retry_model_delta.json"
    retry_delta_path.write_bytes(dumps_canonical(retry_delta))
    retry_verification = verify_revision_delta(retry_proposal, gold_delta)
    retry_gap = compare_deltas(retry_delta, gold_delta).to_dict()
    retry_gap_path = case_output_dir / "retry_gap_report.json"
    _write_json(retry_gap_path, retry_gap)

    ledger_commit = None
    if retry_verification.accepted:
        ledger_commit = commit_verified_revision_delta(
            case_id=case_id,
            model=retry_model,
            clean_pack=clean_pack,
            perturbed_pack=perturbed_pack,
            expected_delta=gold_delta,
            delta=retry_proposal,
            verification=retry_verification,
            ledger_root=ledger_root,
        ).to_dict()

    result["retry"] = {
        "called": True,
        "model": retry_model,
        "json_valid": True,
        "accepted": retry_verification.accepted,
        "reasons": retry_verification.reasons,
        "reason_families": retry_verification.reason_families,
        "gap_summary": retry_gap["summary"],
        "model_delta_path": retry_delta_path.as_posix(),
        "gap_report_path": retry_gap_path.as_posix(),
        "ledger_committed": ledger_commit is not None,
        "ledger_commit": ledger_commit,
    }
    result["no_regression_guard"] = write_best_candidate_artifacts(
        case_output_dir=case_output_dir,
        baseline_delta=baseline_delta,
        baseline_verification=baseline_verification,
        baseline_gap=baseline_gap,
        retry_delta=retry_delta,
        retry_verification=retry_verification,
        retry_gap=retry_gap,
    )
    result["training_effect"] = summarize_training_effect(
        baseline_verification=baseline_verification,
        baseline_gap=baseline_gap,
        retry_verification=retry_verification,
        retry_gap=retry_gap,
    )
    _write_json(case_output_dir / "training_summary.json", result)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return result


def build_retry_messages(
    *,
    proposer: DeepSeekProposer,
    clean_pack: Mapping[str, Any],
    perturbed_pack: Mapping[str, Any],
    case_id: str,
    strict_copy: bool,
    baseline_delta: Mapping[str, Any],
    baseline_verification: Mapping[str, Any],
    baseline_gap: Mapping[str, Any],
    repair_instruction: Mapping[str, Any],
) -> list[dict[str, str]]:
    messages = proposer._build_messages(  # noqa: SLF001
        clean_pack=clean_pack,
        perturbed_pack=perturbed_pack,
        case_id=case_id,
        strict_copy=strict_copy,
    )
    retry_prompt = build_retry_prompt_addendum(
        baseline_delta=baseline_delta,
        baseline_verification=baseline_verification,
        baseline_gap=baseline_gap,
        repair_instruction=repair_instruction,
    )
    return [
        messages[0],
        {
            "role": "user",
            "content": "\n\n".join([messages[1]["content"], retry_prompt]),
        },
    ]


def build_retry_prompt_addendum(
    *,
    baseline_delta: Mapping[str, Any],
    baseline_verification: Mapping[str, Any],
    baseline_gap: Mapping[str, Any],
    repair_instruction: Mapping[str, Any],
) -> str:
    retry_rules = [
        "You are now in an Iota diagnostic retry.",
        "The prior delta was rejected by the deterministic verifier.",
        "Return one complete corrected RevisionDelta JSON object.",
        "Do not return commentary, markdown, or a patch.",
        "Apply only the repair_instruction target changes.",
        "Copy every object in exact_expected_fragments exactly.",
        "Do not alter baseline objects that are already verifier-clean.",
        "Remove unexpected items named in remove_unexpected_items.",
        "Preserve every ID in preservation_constraints.",
        "Use before_rank: null for newly introduced scenarios.",
    ]
    return "\n\n".join(
        [
            "BASELINE_REJECTED_DELTA:",
            _json_block(baseline_delta),
            "VERIFIER_FEEDBACK:",
            _json_block(baseline_verification),
            "BASELINE_GAP_REPORT:",
            _json_block(baseline_gap),
            "DIAGNOSTIC_REPAIR_INSTRUCTION:",
            _json_block(repair_instruction),
            "RETRY_RULES:",
            "\n".join(f"- {rule}" for rule in retry_rules),
        ]
    )


def request_retry_delta(
    proposer: DeepSeekProposer,
    retry_messages: list[dict[str, str]],
) -> RetryDeltaResult | SealedFailureArtifact:
    if not proposer.api_key:
        return proposer._failure(  # noqa: SLF001
            model=proposer.model,
            error_type="missing_api_key",
            message="DEEPSEEK_API_KEY is not set.",
        )
    models = [proposer.model]
    if proposer.fallback_model and proposer.fallback_model not in models:
        models.append(proposer.fallback_model)

    last_failure: SealedFailureArtifact | None = None
    for model in models:
        result = proposer._request_delta(  # noqa: SLF001
            model=model,
            messages=retry_messages,
        )
        if isinstance(result, RevisionDelta):
            return RetryDeltaResult(delta=result, model=model)
        last_failure = result
    if last_failure is not None:
        return last_failure
    return proposer._failure(  # noqa: SLF001
        model=proposer.model,
        error_type="internal_error",
        message="No DeepSeek diagnostic retry request was made.",
    )


def build_proposer(args: argparse.Namespace) -> DeepSeekProposer:
    return DeepSeekProposer(
        model=args.model,
        fallback_model=args.fallback_model,
        timeout_seconds=args.timeout_seconds,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retry one failed DeepSeek CUC case with diagnostic feedback.",
    )
    parser.add_argument("--case-id", default=DEFAULT_CASE_ID)
    parser.add_argument("--params-json", type=Path, default=DEFAULT_PARAMS_PATH)
    parser.add_argument("--baseline-dir", type=Path, default=DEFAULT_BASELINE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--ledger-root",
        type=Path,
        default=None,
        help="Ledger root. Defaults to <output-dir>/ledger.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
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
        "--dry-run",
        action="store_true",
        help="Write repair_instruction and summary without calling DeepSeek.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    output_dir = args.output_dir
    ledger_root = args.ledger_root or output_dir / "ledger"
    proposer = build_proposer(args)
    run_diagnostic_retry(
        case_id=args.case_id,
        params_json=args.params_json,
        baseline_dir=args.baseline_dir,
        output_dir=output_dir,
        ledger_root=ledger_root,
        proposer=proposer,
        strict_copy=args.strict_copy,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
