from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from core.determinism.hashing import sha256_bytes
from core.determinism.replay import verify_run_deterministic

SCHEMA_VERSION = "iv.phase3.customer_evidence.v1"
REPORT_JSON_NAME = "customer_evidence_report.json"
REPORT_MD_NAME = "customer_evidence_report.md"
COMMIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


def build_customer_evidence_package(
    *,
    session_root: Path,
    case_id: str,
    sealed_manifest: Path,
    sealed_repository_commit: str,
    package_dir: Path,
) -> dict[str, Any]:
    _require_empty_package_dir(package_dir)
    scorecard_path = session_root / case_id / "scorecard.json"
    scorecard = _read_object(scorecard_path)
    training_pass = _accepted_training_pass(scorecard)
    pass_index = int(training_pass["pass_index"])
    pass_dir = session_root / "passes" / f"pass_{pass_index:03d}" / case_id

    best_candidate = _object(scorecard.get("best_candidate"), "best_candidate")
    ledger_commit = _object(best_candidate.get("ledger_commit"), "ledger_commit")
    bundle_sha256 = _required_string(ledger_commit, "bundle_sha256")
    ledger_dir = session_root / "ledger" / bundle_sha256

    source_artifacts = {
        "evidence/scorecard.json": scorecard_path,
        "evidence/baseline_gap_report.json": pass_dir / "baseline_gap_report.json",
        "evidence/baseline_model_delta.json": pass_dir / "baseline_model_delta.json",
        "evidence/baseline_verification.json": (
            pass_dir / "baseline_verification.json"
        ),
        "evidence/repair_instruction.json": pass_dir / "repair_instruction.json",
        "evidence/retry_gap_report.json": pass_dir / "retry_gap_report.json",
        "evidence/retry_model_delta.json": pass_dir / "retry_model_delta.json",
        "evidence/training_summary.json": pass_dir / "training_summary.json",
        "evidence/verification.json": pass_dir / "verification.json",
        f"ledger/{bundle_sha256}/attestation.json": ledger_dir / "attestation.json",
        f"ledger/{bundle_sha256}/bundle.json": ledger_dir / "bundle.json",
        f"ledger/{bundle_sha256}/output.json": ledger_dir / "output.json",
    }
    for path in [sealed_manifest, *source_artifacts.values()]:
        if not path.is_file():
            raise FileNotFoundError(path)
    if (pass_dir / "retry_failure.json").exists():
        raise ValueError("accepted evidence package cannot contain retry_failure.json")

    validated = _validate_evidence(
        scorecard=scorecard,
        pass_dir=pass_dir,
        ledger_dir=ledger_dir,
        sealed_manifest=sealed_manifest,
        sealed_repository_commit=sealed_repository_commit,
    )

    package_dir.mkdir(parents=True, exist_ok=True)
    _copy_exact(sealed_manifest, package_dir / "MANIFEST.sha256")
    for relative_path, source_path in sorted(source_artifacts.items()):
        destination = package_dir / relative_path
        if relative_path.startswith("evidence/"):
            _copy_json_canonical(source_path, destination)
        else:
            _copy_exact(source_path, destination)

    package_ledger_dir = package_dir / "ledger" / bundle_sha256
    replay = _strict_replay_with_packaged_manifest(package_dir, package_ledger_dir)
    if replay["ok"] is not True or replay["warnings"]:
        raise ValueError(f"strict replay failed: {replay}")

    artifact_hashes = _artifact_hash_records(
        package_dir,
        ["MANIFEST.sha256", *sorted(source_artifacts)],
    )
    report = _build_report(
        scorecard=scorecard,
        validated=validated,
        replay=replay,
        artifact_hashes=artifact_hashes,
        sealed_repository_commit=sealed_repository_commit,
    )
    _write_json(package_dir / REPORT_JSON_NAME, report)
    (package_dir / REPORT_MD_NAME).write_text(
        render_customer_report(report),
        encoding="utf-8",
        newline="\n",
    )
    return report


def render_customer_report(report: Mapping[str, Any]) -> str:
    session = _object(report.get("session_result"), "session_result")
    repair = _object(report.get("diagnostic_repair"), "diagnostic_repair")
    ledger = _object(report.get("ledger_attestation"), "ledger_attestation")
    replay = _object(report.get("strict_replay"), "strict_replay")
    artifacts = report.get("artifact_hashes", [])

    lines = [
        "# Iota Verbum Customer Evidence Report",
        "",
        f"Evidence status: `{report['evidence_status']}`",
        "",
        "## Executive Summary",
        "",
        str(report["supported_claim"]),
        "",
        "## Verified Service Outcome",
        "",
        "| Stage | Accepted | Similarity | Verifier reasons | Ledger |",
        "| --- | --- | ---: | ---: | --- |",
        (
            f"| Baseline benchmark | {_bool(session['accepted_before'])} | "
            f"{_percent(session['similarity_before'])} | "
            f"{session['verifier_reason_count_before']} | none |"
        ),
        (
            f"| Iota training pass 1 | {_bool(session['accepted_after'])} | "
            f"{_percent(session['similarity_after'])} | "
            f"{session['verifier_reason_count_after']} | committed |"
        ),
        "",
        f"- Model: `{report['model']}`",
        f"- Case: `{report['case_id']}`",
        f"- Provider: `{report['provider']}`",
        f"- Training passes consumed: `{session['training_pass_count']}`",
        f"- Similarity improvement: `+{session['similarity_delta']:.2f}` points",
        f"- No-regression selection: `{session['selected_candidate']}`",
        "",
        "## Deterministic Diagnostic Repair",
        "",
        f"- Failure family: `{repair['failure_family']}`",
        f"- Target operation: `{repair['target_operation_id']}`",
        f"- Repair instruction: {repair['repair_template']}",
        (
            "- Grounding evidence: "
            + ", ".join(f"`{item}`" for item in repair["grounding_evidence_ids"])
        ),
        (
            "- Preservation constraints: "
            + ", ".join(
                f"`{item}`" for item in repair["preservation_constraints"]
            )
        ),
        "",
        "## Sealed Integrity Proof",
        "",
        f"- Bundle SHA-256: `{ledger['bundle_sha256']}`",
        f"- Output SHA-256: `{ledger['output_sha256']}`",
        f"- Attestation SHA-256: `{ledger['attestation_sha256']}`",
        f"- Sealed manifest SHA-256: `{ledger['manifest_sha256']}`",
        f"- Sealed repository commit: `{report['sealed_repository_commit']}`",
        "- Sealed commit manifest match: `verified`",
        f"- Strict replay status: `{replay['status']}`",
        f"- Strict replay warnings: `{len(replay['warnings'])}`",
        "",
        "Reproduce strict replay from the evidence package directory:",
        "",
        "```powershell",
        (
            "python -m core.determinism.replay "
            f"ledger/{ledger['bundle_sha256']} --strict-manifest"
        ),
        "```",
        "",
        "## Included Evidence",
        "",
        "| Artifact | SHA-256 | Bytes |",
        "| --- | --- | ---: |",
    ]
    for artifact in artifacts:
        lines.append(
            f"| `{artifact['path']}` | `{artifact['sha256']}` | "
            f"{artifact['bytes']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            str(report["proof_boundary"]),
            "",
        ]
    )
    return "\n".join(lines)


def _validate_evidence(
    *,
    scorecard: Mapping[str, Any],
    pass_dir: Path,
    ledger_dir: Path,
    sealed_manifest: Path,
    sealed_repository_commit: str,
) -> dict[str, Any]:
    _expect(scorecard.get("schema_version") == "iv.phase3.training_room_wrapper.v1")
    _expect(scorecard.get("service_kind") == "iota_training_room")
    _expect(scorecard.get("allow_live_model") is True)
    _expect(scorecard.get("stop_reason") == "accepted")

    baseline = _object(scorecard.get("baseline"), "baseline")
    best = _object(scorecard.get("best_candidate"), "best_candidate")
    effect = _object(scorecard.get("training_effect"), "training_effect")
    _expect(baseline.get("accepted") is False)
    _expect(best.get("accepted") is True)
    _expect(best.get("ledger_committed") is True)
    _expect(effect.get("improved") is True)
    _expect(effect.get("accepted_before") is False)
    _expect(effect.get("accepted_after") is True)

    training_summary = _read_object(pass_dir / "training_summary.json")
    retry = _object(training_summary.get("retry"), "retry")
    guard = _object(training_summary.get("no_regression_guard"), "no_regression_guard")
    _expect(retry.get("called") is True)
    _expect(retry.get("json_valid") is True)
    _expect(retry.get("accepted") is True)
    _expect(retry.get("ledger_committed") is True)
    _expect(guard.get("selected_candidate") == "retry")
    _expect(guard.get("retry_improved") is True)
    _expect(guard.get("retry_regressed") is False)

    baseline_verification = _read_object(pass_dir / "baseline_verification.json")
    verification = _read_object(pass_dir / "verification.json")
    baseline_gap = _read_object(pass_dir / "baseline_gap_report.json")
    retry_gap = _read_object(pass_dir / "retry_gap_report.json")
    _expect(baseline_verification.get("accepted") is False)
    _expect(verification == {"accepted": True, "reason_families": [], "reasons": []})
    _expect(
        _similarity(baseline_gap)
        == float(effect["similarity_before"])
        == float(baseline["similarity_score_percent"])
    )
    _expect(
        _similarity(retry_gap)
        == float(effect["similarity_after"])
        == float(best["similarity_score_percent"])
    )

    repair = _read_object(pass_dir / "repair_instruction.json")
    _expect(repair.get("candidate_kind") == "repair_instruction")
    _expect(repair.get("case_id") == scorecard.get("case_id"))

    ledger_commit = _object(best.get("ledger_commit"), "ledger_commit")
    attestation_path = ledger_dir / "attestation.json"
    bundle_path = ledger_dir / "bundle.json"
    output_path = ledger_dir / "output.json"
    attestation = _read_object(attestation_path)
    output = _read_object(output_path)
    actual_hashes = {
        "bundle_sha256": _sha256_file(bundle_path),
        "output_sha256": _sha256_file(output_path),
        "attestation_sha256": _sha256_file(attestation_path),
        "manifest_sha256": _sha256_file(sealed_manifest),
    }
    for key in ("bundle_sha256", "output_sha256", "attestation_sha256"):
        _expect(actual_hashes[key] == ledger_commit.get(key))
    _expect(ledger_dir.name == actual_hashes["bundle_sha256"])
    _expect(attestation.get("bundle_sha256") == actual_hashes["bundle_sha256"])
    _expect(attestation.get("output_sha256") == actual_hashes["output_sha256"])
    _expect(attestation.get("manifest_sha256") == actual_hashes["manifest_sha256"])
    _expect(output.get("case_id") == scorecard.get("case_id"))
    _expect(output.get("verifier") == verification)
    _expect(COMMIT_SHA_PATTERN.fullmatch(sealed_repository_commit) is not None)
    _expect(
        _manifest_at_commit(sealed_repository_commit) == sealed_manifest.read_bytes()
    )

    return {
        "attestation": attestation,
        "output": output,
        "repair": repair,
        "training_summary": training_summary,
        "actual_hashes": actual_hashes,
    }


def _build_report(
    *,
    scorecard: Mapping[str, Any],
    validated: Mapping[str, Any],
    replay: Mapping[str, Any],
    artifact_hashes: list[dict[str, Any]],
    sealed_repository_commit: str,
) -> dict[str, Any]:
    effect = _object(scorecard.get("training_effect"), "training_effect")
    pass_items = scorecard.get("training_passes", [])
    training_pass = _accepted_training_pass(scorecard)
    repair = _object(validated.get("repair"), "repair")
    attestation = _object(validated.get("attestation"), "attestation")
    output = _object(validated.get("output"), "output")
    actual_hashes = _object(validated.get("actual_hashes"), "actual_hashes")
    model = _required_string(output, "model")
    similarity_before = float(effect["similarity_before"])
    similarity_after = float(effect["similarity_after"])

    supported_claim = (
        f"In one controlled live session, {model} moved from a verifier-rejected "
        f"{similarity_before:.2f}% baseline to a verifier-accepted "
        f"{similarity_after:.2f}% candidate after one deterministic Iota "
        "diagnostic repair pass, then produced a ledger artifact that passed "
        "strict-manifest replay."
    )
    proof_boundary = (
        "This package proves one live, one-case, in-context diagnostic-repair "
        "session. It does not establish broad benchmark improvement, persistent "
        "weight-level model improvement, fine-tuning, or performance outside the "
        "sealed case and verifier contract."
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_kind": "iota_training_room_customer_evidence",
        "evidence_status": "strict_replay_verified",
        "created_at_utc": attestation["created_utc"],
        "provider": scorecard["provider"],
        "model": model,
        "case_id": scorecard["case_id"],
        "source_case_id": scorecard["source_case_id"],
        "sealed_repository_commit": sealed_repository_commit,
        "sealed_repository_manifest_verified": True,
        "supported_claim": supported_claim,
        "proof_boundary": proof_boundary,
        "session_result": {
            "accepted_before": effect["accepted_before"],
            "accepted_after": effect["accepted_after"],
            "similarity_before": similarity_before,
            "similarity_after": similarity_after,
            "similarity_delta": float(effect["similarity_delta"]),
            "verifier_reason_count_before": effect["verifier_reason_count_before"],
            "verifier_reason_count_after": effect["verifier_reason_count_after"],
            "training_pass_count": len(pass_items),
            "selected_candidate": training_pass["selected_candidate"],
            "retry_regressed": training_pass["retry_regressed"],
        },
        "diagnostic_repair": {
            "failure_family": repair["failure_family"],
            "target_operation_id": repair["target_operation_id"],
            "repair_template": repair["repair_template"],
            "grounding_evidence_ids": repair["grounding_evidence_ids"],
            "preservation_constraints": repair["preservation_constraints"],
        },
        "ledger_attestation": {
            "bundle_sha256": actual_hashes["bundle_sha256"],
            "output_sha256": actual_hashes["output_sha256"],
            "attestation_sha256": actual_hashes["attestation_sha256"],
            "manifest_sha256": actual_hashes["manifest_sha256"],
            "ruleset_id": attestation["ruleset_id"],
            "core_version": attestation["core_version"],
        },
        "strict_replay": {
            "ok": replay["ok"],
            "status": replay["status"],
            "sub_step": replay["sub_step"],
            "warnings": replay["warnings"],
            "bundle_sha256": replay["bundle_sha256"],
            "output_sha256": replay["output_sha256"],
            "attestation_sha256": replay["attestation_sha256"],
        },
        "artifact_hashes": artifact_hashes,
    }


def _accepted_training_pass(scorecard: Mapping[str, Any]) -> Mapping[str, Any]:
    pass_items = scorecard.get("training_passes")
    if not isinstance(pass_items, list):
        raise ValueError("training_passes must be a list")
    accepted = [
        item
        for item in pass_items
        if isinstance(item, Mapping)
        and item.get("called") is True
        and item.get("accepted") is True
        and item.get("ledger_committed") is True
        and item.get("selected_candidate") == "retry"
    ]
    if len(accepted) != 1:
        raise ValueError("expected exactly one accepted committed training pass")
    return accepted[0]


def _artifact_hash_records(
    package_dir: Path,
    relative_paths: list[str],
) -> list[dict[str, Any]]:
    records = []
    for relative_path in sorted(relative_paths):
        path = package_dir / relative_path
        records.append(
            {
                "path": relative_path,
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return records


def _strict_replay_with_packaged_manifest(
    package_dir: Path,
    ledger_dir: Path,
) -> dict[str, Any]:
    resolved_package_dir = package_dir.resolve()
    resolved_ledger_dir = ledger_dir.resolve()
    with _working_directory(resolved_package_dir):
        return verify_run_deterministic(
            resolved_ledger_dir.as_posix(),
            strict_manifest=True,
        )


def _manifest_at_commit(commit_sha: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_sha}:MANIFEST.sha256"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(
            f"unable to read MANIFEST.sha256 from sealed commit {commit_sha}"
        ) from exc
    return result.stdout


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _require_empty_package_dir(package_dir: Path) -> None:
    if package_dir.exists() and any(package_dir.iterdir()):
        raise ValueError(f"package directory must be empty: {package_dir}")


def _copy_exact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def _copy_json_canonical(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_json(destination, _read_object(source))


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _required_string(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"{key} must be a non-empty string")
    return result


def _similarity(gap_report: Mapping[str, Any]) -> float:
    summary = _object(gap_report.get("summary"), "gap_report.summary")
    return float(summary["similarity_score_percent"])


def _sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _expect(condition: bool) -> None:
    if not condition:
        raise ValueError("evidence validation failed")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _percent(value: Any) -> str:
    return f"{float(value):.2f}%"


def _bool(value: Any) -> str:
    return "true" if bool(value) else "false"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a strict-replay-verified Phase 3 customer evidence package."
    )
    parser.add_argument("--session-root", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--sealed-manifest", type=Path, required=True)
    parser.add_argument("--sealed-repository-commit", required=True)
    parser.add_argument("--package-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_customer_evidence_package(
        session_root=args.session_root,
        case_id=args.case_id,
        sealed_manifest=args.sealed_manifest,
        sealed_repository_commit=args.sealed_repository_commit,
        package_dir=args.package_dir,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
