"""Examiner export pack — the deterministic report a customer hands to an auditor.

Aggregates a set of sealed decision records into a single, hash-stamped bundle
that summarises outcomes, adverse-action coverage, verification status, and
compliance warnings, with a manifest of per-record hashes an auditor can
independently re-verify.
"""

from __future__ import annotations

from pathlib import Path

from core.attestation import canonicalize_json, compute_sha256
from provenant.record import ADVERSE_OUTCOMES, verify_record

EXPORT_SCHEMA = "provenant.examiner_pack.v1"


def build_examiner_pack(
    record_dirs: list[Path],
    *,
    tenant_id: str,
    generated_utc: str,
) -> dict:
    """Build a deterministic examiner pack from sealed record directories."""
    records = []
    outcome_counts: dict[str, int] = {}
    adverse_total = 0
    adverse_with_reasons = 0
    warning_total = 0
    verified_total = 0

    for record_dir in sorted(Path(d) for d in record_dirs):
        verification = verify_record(record_dir)
        import json

        record = json.loads((record_dir / "record.json").read_text(encoding="utf-8"))

        outcome = str((record.get("decision") or {}).get("outcome", "")).upper()
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        if outcome in ADVERSE_OUTCOMES:
            adverse_total += 1
            if record.get("reason_codes"):
                adverse_with_reasons += 1
        warnings = record.get("compliance_warnings", [])
        warning_total += len(warnings)
        if verification["verified"]:
            verified_total += 1

        records.append(
            {
                "record_id": record.get("record_id"),
                "subject_ref": record.get("subject_ref"),
                "outcome": outcome,
                "record_sha256": verification["recorded_file_sha256"],
                "content_sha256": verification["recorded_content_sha256"],
                "verified": verification["verified"],
                "compliance_warnings": warnings,
            }
        )

    records.sort(key=lambda r: (r["subject_ref"] or "", r["record_id"] or ""))

    pack = {
        "schema": EXPORT_SCHEMA,
        "tenant_id": tenant_id,
        "generated_utc": generated_utc,
        "summary": {
            "record_count": len(records),
            "verified_count": verified_total,
            "outcome_counts": dict(sorted(outcome_counts.items())),
            "adverse_action": {
                "adverse_decisions": adverse_total,
                "with_reason_codes": adverse_with_reasons,
                "coverage": (
                    round(adverse_with_reasons / adverse_total, 4)
                    if adverse_total
                    else 1.0
                ),
            },
            "compliance_warning_count": warning_total,
        },
        "records": records,
    }
    pack["pack_sha256"] = compute_sha256(canonicalize_json(pack))
    return pack


def write_examiner_pack(pack: dict, out_path: Path) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonicalize_json(pack)
    out_path.write_bytes(payload)
    return compute_sha256(payload)
