from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.cuc_harness.verifier import DeltaVerificationResult
from core.determinism.canonical_json import dumps_canonical
from core.determinism.finalize import finalize
from core.determinism.ledger import write_run
from core.determinism.manifest_hash import compute_manifest_sha256

CUC_LEDGER_RULESET_ID = "ruleset.cuc_harness.structured_delta.v1"
CUC_LEDGER_OUTPUT_SCHEMA_VERSION = "iv.cuc_harness.ledgered_revision.v1"


@dataclass(frozen=True)
class LedgerCommitResult:
    run_dir: Path
    bundle_sha256: str
    output_sha256: str
    attestation_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "run_dir": self.run_dir.as_posix(),
            "bundle_sha256": self.bundle_sha256,
            "output_sha256": self.output_sha256,
            "attestation_sha256": self.attestation_sha256,
        }


def commit_verified_revision_delta(
    *,
    case_id: str,
    model: str,
    clean_pack: Mapping[str, Any],
    perturbed_pack: Mapping[str, Any],
    delta: Any,
    verification: DeltaVerificationResult,
    ledger_root: Path,
    expected_delta: Mapping[str, Any] | None = None,
    manifest_sha256: str | None = None,
    core_version: str = "0.3.0",
    created_utc: str | None = None,
    ruleset_id: str = CUC_LEDGER_RULESET_ID,
) -> LedgerCommitResult:
    if not verification.accepted:
        raise ValueError("only accepted RevisionDelta proposals can be committed")

    timestamp = created_utc or _utc_timestamp()
    evidence_bundle = build_cuc_evidence_bundle(
        case_id=case_id,
        model=model,
        clean_pack=clean_pack,
        perturbed_pack=perturbed_pack,
        expected_delta=expected_delta,
        created_utc=timestamp,
        ruleset_id=ruleset_id,
        core_version=core_version,
    )
    output_obj = {
        "schema_version": CUC_LEDGER_OUTPUT_SCHEMA_VERSION,
        "case_id": case_id,
        "model": model,
        "delta": _as_payload(delta),
        "verifier": verification.to_dict(),
    }
    effective_manifest_sha256 = (
        manifest_sha256
        if manifest_sha256 is not None
        else compute_manifest_sha256()
    )
    sealed = finalize(
        evidence_bundle,
        output_obj,
        manifest_sha256=effective_manifest_sha256,
        core_version=core_version,
        ruleset_id=ruleset_id,
        created_utc=timestamp,
    )
    run_dir = write_run(ledger_root=ledger_root.as_posix(), **sealed)
    return LedgerCommitResult(
        run_dir=run_dir,
        bundle_sha256=sealed["bundle_sha256"],
        output_sha256=sealed["output_sha256"],
        attestation_sha256=sealed["attestation_sha256"],
    )


def build_cuc_evidence_bundle(
    *,
    case_id: str,
    model: str,
    clean_pack: Mapping[str, Any],
    perturbed_pack: Mapping[str, Any],
    expected_delta: Mapping[str, Any] | None,
    created_utc: str,
    ruleset_id: str = CUC_LEDGER_RULESET_ID,
    core_version: str = "0.3.0",
) -> dict[str, Any]:
    artifacts = [
        _json_artifact(case_id, "clean_pack", clean_pack),
        _json_artifact(case_id, "perturbed_pack", perturbed_pack),
    ]
    if expected_delta is not None:
        artifacts.append(_json_artifact(case_id, "expected_delta", expected_delta))
    return {
        "bundle_version": "1.0",
        "created_utc": created_utc,
        "inputs": {
            "prompt": "CUC structured RevisionDelta proposal",
            "params": {
                "case_id": case_id,
                "model": model,
                "mode": "cuc_harness_structured_revision",
            },
        },
        "artifacts": artifacts,
        "toolchain": {
            "core_version": core_version,
            "parser_versions": {
                "cuc_harness": "1.0",
            },
            "schema_versions": {
                "evidence_bundle": "1.0",
                "attestation_record": "1.0",
            },
        },
        "policy": {
            "ruleset_id": ruleset_id,
        },
    }


def _json_artifact(
    case_id: str,
    chunk_id: str,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    text = dumps_canonical(value).decode("utf-8")
    return {
        "source_id": f"cuc:{case_id}",
        "chunk_id": chunk_id,
        "offset_start": 0,
        "offset_end": len(text),
        "text": text,
    }


def _as_payload(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json")
        if isinstance(payload, Mapping):
            return payload
    raise TypeError("delta must be a mapping or expose model_dump(mode='json').")


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


__all__ = [
    "CUC_LEDGER_OUTPUT_SCHEMA_VERSION",
    "CUC_LEDGER_RULESET_ID",
    "LedgerCommitResult",
    "build_cuc_evidence_bundle",
    "commit_verified_revision_delta",
]
