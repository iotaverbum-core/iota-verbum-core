"""Provenant decision records.

A *decision record* is a deterministic, tamper-evident receipt for a single
AI-assisted decision (e.g. an underwriting outcome). It reuses the repo's
determinism primitives so that the same decision always seals to the same
bytes and the same hash, and so any later mutation is detectable.

The record carries two independent integrity anchors:

* ``seal.content_sha256`` — hash of the canonicalised decision content
  (everything except the seal). Detects content tampering regardless of file
  formatting.
* the sidecar ``attestation.sha256`` written next to ``record.json`` — hash of
  the exact file bytes. Detects file-level tampering.

Determinism contract: ``seal_decision`` performs no wall-clock reads and no
randomness. ``created_utc`` is supplied by the caller.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from core.attestation import canonicalize_json, compute_sha256

RECORD_SCHEMA = "provenant.decision_record.v1"
SEAL_ALGO = "sha256-canonical-json"

# Outcomes that trigger an adverse-action obligation (ECOA / Reg B).
ADVERSE_OUTCOMES = {"DENY", "DECLINE", "REJECT", "ADVERSE", "COUNTEROFFER"}


def _content_view(record: dict) -> dict:
    """Return the record without its volatile/seal fields for content hashing."""
    view = deepcopy(record)
    view.pop("seal", None)
    return view


def evaluate_compliance(record: dict) -> list[dict]:
    """Return structured compliance warnings for a decision record.

    The first-class check: an adverse outcome with no reason codes would fail an
    ECOA / Reg B adverse-action notice requirement. This is exactly the kind of
    silent gap that surfaces in an audit.
    """
    warnings: list[dict] = []
    decision = record.get("decision") or {}
    outcome = str(decision.get("outcome", "")).upper()
    reason_codes = record.get("reason_codes") or []
    governance = record.get("governance") or {}

    if outcome in ADVERSE_OUTCOMES and not reason_codes:
        warnings.append(
            {
                "code": "ADVERSE_ACTION_NO_REASONS",
                "severity": "high",
                "regulation": "ECOA / Reg B",
                "message": (
                    f"Adverse outcome '{outcome}' has no reason codes; an "
                    "adverse-action notice cannot be substantiated."
                ),
            }
        )

    if governance.get("adverse_action_required") and outcome not in ADVERSE_OUTCOMES:
        warnings.append(
            {
                "code": "ADVERSE_FLAG_OUTCOME_MISMATCH",
                "severity": "medium",
                "regulation": "ECOA / Reg B",
                "message": (
                    "Record marked adverse_action_required but outcome "
                    f"'{outcome}' is not an adverse outcome."
                ),
            }
        )

    # Evidence cited by a reason code must exist in the evidence list.
    evidence_refs = {e.get("ref") for e in (record.get("evidence") or [])}
    for reason in reason_codes:
        cited = reason.get("evidence_ref")
        if cited and cited not in evidence_refs:
            warnings.append(
                {
                    "code": "REASON_EVIDENCE_MISSING",
                    "severity": "medium",
                    "regulation": "model-risk / SR 11-7",
                    "message": (
                        f"Reason code '{reason.get('code')}' cites evidence "
                        f"'{cited}' that is not attached to the record."
                    ),
                }
            )

    return warnings


def seal_decision(
    *,
    record_id: str,
    tenant_id: str,
    created_utc: str,
    subject_ref: str,
    decision: dict,
    model: dict,
    evidence: list[dict] | None = None,
    reason_codes: list[dict] | None = None,
    governance: dict | None = None,
    prior_record_sha256: str | None = None,
) -> dict:
    """Seal a single AI-assisted decision into a deterministic record dict."""
    record: dict = {
        "schema": RECORD_SCHEMA,
        "record_id": record_id,
        "tenant_id": tenant_id,
        "created_utc": created_utc,
        "subject_ref": subject_ref,
        "decision": decision,
        "reason_codes": list(reason_codes or []),
        "model": model,
        "evidence": list(evidence or []),
        "governance": governance or {"audit_ready": True},
        "links": {"prior_record_sha256": prior_record_sha256},
    }
    record["compliance_warnings"] = evaluate_compliance(record)

    content_sha256 = compute_sha256(canonicalize_json(_content_view(record)))
    record["seal"] = {
        "algo": SEAL_ALGO,
        "content_sha256": content_sha256,
    }
    return record


def write_record(record: dict, out_dir: Path) -> dict:
    """Write ``record.json`` + ``attestation.sha256`` deterministically."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    record_path = out_dir / "record.json"
    attestation_path = out_dir / "attestation.sha256"

    payload = canonicalize_json(record)
    record_path.write_bytes(payload)
    record_sha256 = compute_sha256(payload)
    attestation_path.write_text(record_sha256 + "\n", encoding="utf-8", newline="\n")

    return {
        "record_path": str(record_path),
        "attestation_path": str(attestation_path),
        "record_sha256": record_sha256,
        "content_sha256": record["seal"]["content_sha256"],
    }


def verify_record(record_dir: Path) -> dict:
    """Independently verify a sealed record directory.

    Recomputes both the file-level attestation and the content-level seal and
    reports any mismatch (the tamper-evidence an auditor checks).
    """
    record_dir = Path(record_dir)
    record_path = record_dir / "record.json"
    attestation_path = record_dir / "attestation.sha256"

    file_bytes = record_path.read_bytes()
    computed_file_sha = compute_sha256(file_bytes)
    recorded_file_sha = attestation_path.read_text(encoding="utf-8").strip()

    record = _load_json(file_bytes)
    recorded_content_sha = (record.get("seal") or {}).get("content_sha256")
    computed_content_sha = compute_sha256(canonicalize_json(_content_view(record)))

    file_match = computed_file_sha == recorded_file_sha
    content_match = computed_content_sha == recorded_content_sha
    return {
        "record_id": record.get("record_id"),
        "file_match": file_match,
        "content_match": content_match,
        "verified": file_match and content_match,
        "computed_file_sha256": computed_file_sha,
        "recorded_file_sha256": recorded_file_sha,
        "computed_content_sha256": computed_content_sha,
        "recorded_content_sha256": recorded_content_sha,
        "compliance_warnings": record.get("compliance_warnings", []),
    }


def _load_json(data: bytes) -> dict:
    import json

    return json.loads(data.decode("utf-8"))
