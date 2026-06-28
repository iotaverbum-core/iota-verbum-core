"""Tenant-scoped storage + orchestration for Provenant decision records.

Thin web service over the deterministic ``provenant`` core. Records are sealed
to a per-tenant directory tree so the first paid pilot can run against real
decisions through the API without a database. The sealed bytes are identical to
the ``provenant`` CLI output (byte-for-byte parity), preserving determinism.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from iota_verbum_api.config import settings
from provenant.diff import diff_records
from provenant.export import build_examiner_pack
from provenant.record import seal_decision, verify_record, write_record

_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class DecisionNotFound(Exception):
    """Raised when a record id is not present for the tenant."""


class InvalidRecordId(Exception):
    """Raised when a record id is not filesystem-safe."""


def _storage_root() -> Path:
    return Path(os.getenv("PROVENANT_STORAGE_DIR", settings.provenant_storage_dir))


def _safe_id(record_id: str) -> str:
    if not record_id or not _SAFE_ID.match(record_id):
        raise InvalidRecordId(record_id)
    return record_id


def _tenant_root(tenant_id: str) -> Path:
    return _storage_root() / _safe_id(tenant_id)


def _record_dir(tenant_id: str, record_id: str) -> Path:
    return _tenant_root(tenant_id) / _safe_id(record_id)


def _load_record(tenant_id: str, record_id: str) -> dict:
    record_path = _record_dir(tenant_id, record_id) / "record.json"
    if not record_path.exists():
        raise DecisionNotFound(record_id)
    return json.loads(record_path.read_text(encoding="utf-8"))


def seal(tenant_id: str, payload: dict) -> dict:
    """Seal a decision for ``tenant_id`` and persist it. Returns a summary."""
    record = seal_decision(
        record_id=_safe_id(payload["record_id"]),
        tenant_id=tenant_id,
        created_utc=payload["created_utc"],
        subject_ref=payload["subject_ref"],
        decision=payload["decision"],
        model=payload["model"],
        evidence=payload.get("evidence"),
        reason_codes=payload.get("reason_codes"),
        governance=payload.get("governance"),
        prior_record_sha256=payload.get("prior_record_sha256"),
    )
    written = write_record(record, _record_dir(tenant_id, payload["record_id"]))
    return {
        "record_id": record["record_id"],
        "record_sha256": written["record_sha256"],
        "content_sha256": written["content_sha256"],
        "compliance_warnings": record["compliance_warnings"],
        "verify_url": f"/v1/decisions/{record['record_id']}/verify",
    }


def verify(tenant_id: str, record_id: str) -> dict:
    record_dir = _record_dir(tenant_id, record_id)
    if not (record_dir / "record.json").exists():
        raise DecisionNotFound(record_id)
    return verify_record(record_dir)


def diff(tenant_id: str, prior_record_id: str, current_record_id: str) -> dict:
    prior = _load_record(tenant_id, prior_record_id)
    current = _load_record(tenant_id, current_record_id)
    return diff_records(prior, current)


def export(
    tenant_id: str, generated_utc: str, record_ids: list[str] | None = None
) -> dict:
    tenant_root = _tenant_root(tenant_id)
    if record_ids:
        record_dirs = [_record_dir(tenant_id, rid) for rid in record_ids]
        for rid, rdir in zip(record_ids, record_dirs):
            if not (rdir / "record.json").exists():
                raise DecisionNotFound(rid)
    else:
        record_dirs = sorted(
            child
            for child in tenant_root.glob("*")
            if (child / "record.json").exists()
        )
    return build_examiner_pack(
        record_dirs,
        tenant_id=tenant_id,
        generated_utc=generated_utc,
    )
