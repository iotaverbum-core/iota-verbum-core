from __future__ import annotations

import argparse
import json
import os
import re
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

from scripts.claude_cuc_24_production_probe import (  # noqa: E402
    DEFAULT_PARAMS_PATH,
    load_case_specs,
)
from scripts.delta_gap_diagnostic import compare_deltas  # noqa: E402

from core.cuc_harness.claude_proposer import (  # noqa: E402
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_CLAUDE_RATE_LIMIT_RETRIES,
    DEFAULT_CLAUDE_RATE_LIMIT_SLEEP_SECONDS,
    ClaudeProposer,
)
from core.cuc_harness.deepseek_proposer import (  # noqa: E402
    RevisionDelta,
    SealedFailureArtifact,
)
from core.cuc_harness.ledger_commit import commit_verified_revision_delta  # noqa: E402
from core.cuc_harness.verifier import (  # noqa: E402
    DeltaVerificationResult,
    verify_revision_delta,
)
from core.determinism.canonical_json import dumps_canonical  # noqa: E402

DEFAULT_CASE_ID = "CUCV4-INVARIANT-01-COUNTERPARTY-RESPONSE-LEGAL-CONTRACT"
DEFAULT_BASELINE_DIR = (
    REPO_ROOT / "cuc-results" / "claude_single_case_diagnostic_probe"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cuc-results" / "claude_diagnostic_retry_probe"
SCHEMA_VERSION = "iv.cuc_harness.claude_phase3_diagnostic_retry.v1"
DIAGNOSTIC_CLASSES = (
    "ACCEPTED",
    "SCHEMA_VIOLATION",
    "GROUNDING_GAP",
    "PRESERVATION_BREACH",
    "LAW_FAMILY_MISMATCH",
    "UNCLASSIFIED",
)
REPAIR_INSTRUCTION_TEMPLATES = {
    "SCHEMA_VIOLATION": (
        "Rebuild the RevisionDelta so every required top-level field and typed "
        "operation payload matches the sealed schema."
    ),
    "GROUNDING_GAP": (
        "Patch only the cited grounding gap: add the missing source_op_ids and "
        "supporting_evidence_map entries, and remove any unsupported evidence "
        "references."
    ),
    "PRESERVATION_BREACH": (
        "Restore every preserved or forbidden sibling item and keep those IDs "
        "out of changed state, edge, event, unknown, and scenario buckets."
    ),
    "LAW_FAMILY_MISMATCH": (
        "Align the changed IDs, scenario ranks, and named evidence artifact "
        "with the sealed expected delta without widening the revision scope."
    ),
}

_CHANGE_FIELDS = (
    "changed_states",
    "changed_edges",
    "changed_events",
    "new_unknowns",
    "resolved_unknowns",
)
_EXPLICIT_REASON_FAMILY_CLASS: dict[str, str] = {
    "invalid_json": "SCHEMA_VIOLATION",
    "invalid_structure": "SCHEMA_VIOLATION",
    "response_schema_violation": "SCHEMA_VIOLATION",
    "missing_scenario_rank_changes": "LAW_FAMILY_MISMATCH",
    "unexpected_scenario_rank_changes": "LAW_FAMILY_MISMATCH",
    "mismatched_scenario_rank_changes": "LAW_FAMILY_MISMATCH",
    "missing_supporting_evidence": "GROUNDING_GAP",
    "unexpected_supporting_evidence": "GROUNDING_GAP",
    "mismatched_supporting_evidence": "GROUNDING_GAP",
    "forbidden_revision_touched": "PRESERVATION_BREACH",
    "missing_preserved_items": "PRESERVATION_BREACH",
    "named_evidence_artifact_mismatch": "GROUNDING_GAP",
}
for _field_name in _CHANGE_FIELDS:
    _EXPLICIT_REASON_FAMILY_CLASS[f"missing_{_field_name}"] = "LAW_FAMILY_MISMATCH"
    _EXPLICIT_REASON_FAMILY_CLASS[f"unexpected_{_field_name}"] = (
        "LAW_FAMILY_MISMATCH"
    )
    _EXPLICIT_REASON_FAMILY_CLASS[f"mismatched_{_field_name}"] = (
        "LAW_FAMILY_MISMATCH"
    )

_SOURCE_OP_PATH_RE = re.compile(
    r"^\$\.(?P<section>[^\[]+)\[id='(?P<item_id>[^']+)'\]"
    r"\.source_op_ids\[value='(?P<op_id>[^']+)'\]$"
)
_SUPPORT_PATH_RE = re.compile(
    r'^\$\.supporting_evidence_map\["(?P<item_id>[^"]+)"\]'
)
_SCENARIO_PATH_RE = re.compile(
    r"^\$\.scenario_rank_changes\[scenario_id='(?P<scenario_id>[^']+)'\]"
)


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
    proposer: ClaudeProposer,
    strict_copy: bool,
    dry_run: bool,
) -> dict[str, Any]:
    spec = load_case_specs(params_json, [case_id], None)[0]
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
        _write_json(case_output_dir / "training_summary.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return result

    retry_prompt = build_retry_prompt(
        proposer=proposer,
        clean_pack=clean_pack,
        perturbed_pack=perturbed_pack,
        case_id=case_id,
        strict_copy=strict_copy,
        baseline_delta=baseline_delta,
        baseline_verification=baseline_verification,
        baseline_gap=baseline_gap,
        repair_instruction=repair_instruction,
    )
    retry_result = request_retry_delta(proposer, retry_prompt)
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
    result["training_effect"] = summarize_training_effect(
        baseline_verification=baseline_verification,
        baseline_gap=baseline_gap,
        retry_verification=retry_verification,
        retry_gap=retry_gap,
    )
    _write_json(case_output_dir / "training_summary.json", result)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return result


def build_repair_instruction(
    *,
    case_id: str,
    verification: DeltaVerificationResult,
    gap_report: Mapping[str, Any],
    expected_delta: Mapping[str, Any],
) -> dict[str, Any]:
    failure_family = classify_failure_family(verification, gap_report)
    source_op_requirements = _source_op_requirements(gap_report)
    support_map = _string_list_map(expected_delta.get("supporting_evidence_map", {}))
    required_fields: dict[str, Any] = {
        "exact_expected_fragments": _exact_expected_fragments(
            verification,
            expected_delta,
        ),
        "source_op_ids_required": source_op_requirements,
        "scenario_rank_changes": expected_delta.get("scenario_rank_changes", []),
        "supporting_evidence_map_required": support_map,
        "preserved_items": expected_delta.get("preserved_items", []),
        "forbidden_revisions": expected_delta.get("forbidden_revisions", []),
        "must_preserve_claims": expected_delta.get("must_preserve_claims", []),
        "must_revise_claims": expected_delta.get("must_revise_claims", []),
        "named_evidence_artifact": expected_delta.get("named_evidence_artifact", ""),
        "remove_unexpected_items": _unexpected_items(verification, gap_report),
    }
    source_ids = sorted(source_op_requirements)
    op_ids = sorted(
        {op_id for values in source_op_requirements.values() for op_id in values}
    )
    if source_ids:
        required_fields["source_op_ids_required_on"] = source_ids
    if op_ids:
        required_fields["source_op_ids_value"] = op_ids

    return {
        "candidate_kind": "repair_instruction",
        "case_id": case_id,
        "failure_family": failure_family,
        "target_operation_id": op_ids[0] if len(op_ids) == 1 else "multiple",
        "repair_template": REPAIR_INSTRUCTION_TEMPLATES.get(failure_family, ""),
        "required_fields": required_fields,
        "grounding_evidence_ids": _evidence_ids_from_support_map(support_map),
        "preservation_constraints": expected_delta.get("preserved_items", []),
        "verifier_feedback": verification.to_dict(),
        "gap_summary": gap_report.get("summary", {}),
    }


def classify_failure_family(
    verification: DeltaVerificationResult,
    gap_report: Mapping[str, Any],
) -> str:
    if verification.accepted and not verification.reason_families:
        return "ACCEPTED"
    families = set(verification.reason_families)
    unknown = sorted(families - set(_EXPLICIT_REASON_FAMILY_CLASS))
    if unknown:
        raise ValueError(
            "unclassified verifier reason families: " + ", ".join(unknown)
        )
    classes = {_EXPLICIT_REASON_FAMILY_CLASS[family] for family in families}
    if _source_op_requirements(gap_report):
        return "GROUNDING_GAP"
    if "SCHEMA_VIOLATION" in classes:
        return "SCHEMA_VIOLATION"
    if "PRESERVATION_BREACH" in classes:
        return "PRESERVATION_BREACH"
    if "GROUNDING_GAP" in classes:
        return "GROUNDING_GAP"
    if "LAW_FAMILY_MISMATCH" in classes:
        return "LAW_FAMILY_MISMATCH"
    raise ValueError("cannot classify verifier rejection with no reason families")


def build_retry_prompt(
    *,
    proposer: ClaudeProposer,
    clean_pack: Mapping[str, Any],
    perturbed_pack: Mapping[str, Any],
    case_id: str,
    strict_copy: bool,
    baseline_delta: Mapping[str, Any],
    baseline_verification: DeltaVerificationResult,
    baseline_gap: Mapping[str, Any],
    repair_instruction: Mapping[str, Any],
) -> str:
    base_prompt = proposer._build_user_prompt(  # noqa: SLF001
        clean_pack=clean_pack,
        perturbed_pack=perturbed_pack,
        case_id=case_id,
        strict_copy=strict_copy,
    )
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
            base_prompt,
            "BASELINE_REJECTED_DELTA:",
            _json_block(baseline_delta),
            "VERIFIER_FEEDBACK:",
            _json_block(baseline_verification.to_dict()),
            "BASELINE_GAP_REPORT:",
            _json_block(baseline_gap),
            "DIAGNOSTIC_REPAIR_INSTRUCTION:",
            _json_block(repair_instruction),
            "RETRY_RULES:",
            "\n".join(f"- {rule}" for rule in retry_rules),
        ]
    )


def request_retry_delta(
    proposer: ClaudeProposer,
    retry_prompt: str,
) -> RetryDeltaResult | SealedFailureArtifact:
    if not proposer.api_key:
        return proposer._failure(  # noqa: SLF001
            model=proposer.model,
            error_type="missing_api_key",
            message="ANTHROPIC_API_KEY or CLAUDE_API_KEY is not set.",
        )
    models = [proposer.model]
    if proposer.fallback_model and proposer.fallback_model not in models:
        models.append(proposer.fallback_model)

    last_failure: SealedFailureArtifact | None = None
    for model in models:
        result = proposer._request_delta(model=model, user_prompt=retry_prompt)  # noqa: SLF001
        if isinstance(result, RevisionDelta):
            return RetryDeltaResult(delta=result, model=model)
        last_failure = result
    if last_failure is not None:
        return last_failure
    return proposer._failure(  # noqa: SLF001
        model=proposer.model,
        error_type="internal_error",
        message="No Claude diagnostic retry request was made.",
    )


def summarize_training_effect(
    *,
    baseline_verification: DeltaVerificationResult,
    baseline_gap: Mapping[str, Any],
    retry_verification: DeltaVerificationResult,
    retry_gap: Mapping[str, Any],
) -> dict[str, Any]:
    baseline_score = _similarity_score(baseline_gap)
    retry_score = _similarity_score(retry_gap)
    return {
        "accepted_before": baseline_verification.accepted,
        "accepted_after": retry_verification.accepted,
        "similarity_before": baseline_score,
        "similarity_after": retry_score,
        "similarity_delta": round(retry_score - baseline_score, 6),
        "verifier_reason_count_before": len(baseline_verification.reasons),
        "verifier_reason_count_after": len(retry_verification.reasons),
        "improved": retry_verification.accepted
        or retry_score > baseline_score
        or len(retry_verification.reasons) < len(baseline_verification.reasons),
    }


def resolve_baseline_case_dir(baseline_dir: Path, case_id: str) -> Path:
    candidates = [
        baseline_dir,
        baseline_dir / case_id,
        baseline_dir / _safe_name(case_id),
    ]
    for candidate in candidates:
        if (candidate / "model_delta.json").is_file():
            return candidate
    raise FileNotFoundError(
        "could not find baseline model_delta.json under "
        f"{baseline_dir.as_posix()} for {case_id}"
    )


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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retry one failed Claude CUC case with diagnostic feedback.",
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
    )
    parser.add_argument(
        "--rate-limit-sleep-seconds",
        type=float,
        default=DEFAULT_CLAUDE_RATE_LIMIT_SLEEP_SECONDS,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write repair_instruction and summary without calling Claude.",
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


def _load_or_compare_gap_report(
    baseline_case_dir: Path,
    baseline_delta: Mapping[str, Any],
    gold_delta: Mapping[str, Any],
) -> dict[str, Any]:
    gap_path = baseline_case_dir / "gap_report.json"
    if gap_path.is_file():
        gap_report = _read_json(gap_path)
        if isinstance(gap_report, dict):
            return gap_report
    return compare_deltas(baseline_delta, gold_delta).to_dict()


def _source_op_requirements(gap_report: Mapping[str, Any]) -> dict[str, list[str]]:
    requirements: dict[str, set[str]] = {}
    for path in gap_report.get("missing_fields", []):
        if not isinstance(path, str):
            continue
        match = _SOURCE_OP_PATH_RE.match(path)
        if match is None:
            continue
        requirements.setdefault(match["item_id"], set()).add(match["op_id"])
    return {
        item_id: sorted(op_ids)
        for item_id, op_ids in sorted(requirements.items())
    }


def _unexpected_items(
    verification: DeltaVerificationResult,
    gap_report: Mapping[str, Any],
) -> list[str]:
    unexpected: set[str] = set()
    for reason in verification.reasons:
        if reason.startswith("unexpected_scenario_rank_changes:"):
            unexpected.update(_reason_ids(reason))
        if reason.startswith("unexpected_supporting_evidence:"):
            unexpected.update(
                f"supporting_evidence_map.{item_id}"
                for item_id in _reason_ids(reason)
            )

    for path in gap_report.get("extra_fields", []):
        if not isinstance(path, str):
            continue
        support_match = _SUPPORT_PATH_RE.match(path)
        if support_match is not None:
            unexpected.add(f"supporting_evidence_map.{support_match['item_id']}")
            continue
        scenario_match = _SCENARIO_PATH_RE.match(path)
        if scenario_match is not None:
            unexpected.add(scenario_match["scenario_id"])
            continue
        if ".before" in path and "new_unknowns" in path:
            unexpected.add("new_unknowns[*].before")
            continue
        unexpected.add(path.removeprefix("$."))
    return sorted(unexpected)


def _reason_ids(reason: str) -> list[str]:
    _, _, raw_ids = reason.partition(":")
    return [item for item in raw_ids.split(",") if item]


def _exact_expected_fragments(
    verification: DeltaVerificationResult,
    expected_delta: Mapping[str, Any],
) -> dict[str, Any]:
    fragments: dict[str, Any] = {}
    list_fields = {
        "changed_states": "id",
        "changed_edges": "id",
        "changed_events": "id",
        "new_unknowns": "id",
        "resolved_unknowns": "id",
        "scenario_rank_changes": "scenario_id",
    }
    for field_name, id_key in list_fields.items():
        ids = _reason_target_ids(verification, field_name)
        if not ids:
            continue
        expected_items = _index_expected_items(expected_delta.get(field_name), id_key)
        matched = [
            expected_items[item_id]
            for item_id in ids
            if item_id in expected_items
        ]
        if matched:
            fragments[field_name] = matched

    support_ids = _reason_target_ids(verification, "supporting_evidence")
    support_map = _string_list_map(expected_delta.get("supporting_evidence_map", {}))
    matched_support = {
        item_id: support_map[item_id]
        for item_id in sorted(support_ids)
        if item_id in support_map
    }
    if matched_support:
        fragments["supporting_evidence_map"] = matched_support
    return fragments


def _reason_target_ids(
    verification: DeltaVerificationResult,
    field_name: str,
) -> list[str]:
    prefixes = (
        f"missing_{field_name}:",
        f"mismatched_{field_name}:",
        f"unexpected_{field_name}:",
    )
    target_ids: set[str] = set()
    for reason in verification.reasons:
        if reason.startswith(prefixes):
            target_ids.update(_reason_ids(reason))
    return sorted(target_ids)


def _index_expected_items(value: Any, id_key: str) -> dict[str, Any]:
    if not isinstance(value, list):
        return {}
    indexed: dict[str, Any] = {}
    for item in value:
        if isinstance(item, Mapping) and isinstance(item.get(id_key), str):
            indexed[str(item[id_key])] = item
    return indexed


def _string_list_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, list[str]] = {}
    for key, values in value.items():
        if not isinstance(key, str) or not isinstance(values, list):
            continue
        result[key] = sorted(str(item) for item in values if isinstance(item, str))
    return dict(sorted(result.items()))


def _evidence_ids_from_support_map(support_map: Mapping[str, list[str]]) -> list[str]:
    return sorted(
        {evidence_id for values in support_map.values() for evidence_id in values}
    )


def _similarity_score(gap_report: Mapping[str, Any]) -> float:
    summary = gap_report.get("summary", {})
    if not isinstance(summary, Mapping):
        return 0.0
    value = summary.get("similarity_score_percent", 0.0)
    return float(value) if isinstance(value, int | float) else 0.0


def _json_block(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


if __name__ == "__main__":
    raise SystemExit(main())
