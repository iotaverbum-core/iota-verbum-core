from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import select

from iota_verbum_api.config import settings
from iota_verbum_api.constants import NEUROSYMBOLIC_BOUNDARY
from iota_verbum_api.db.models import DocumentInput, ProvenanceRecord
from iota_verbum_api.db.session import new_session
from iota_verbum_api.services.audit import create_audit_entry
from iota_verbum_api.utils import now_utc


async def enforce_retention_policy() -> int:
    deleted = 0
    cutoff = now_utc() - timedelta(days=settings.retention_days_document_input)
    archive_cutoff = now_utc() - timedelta(days=settings.retention_days_provenance_record)
    with new_session() as db:
        stale = db.scalars(
            select(DocumentInput).where(DocumentInput.created_at < cutoff)
        ).all()
        for row in stale:
            db.delete(row)
            deleted += 1

        db.add(
            create_audit_entry(
                event_type="retention.purge",
                tenant_id=None,
                api_key_hash="",
                endpoint="/system/retention",
                method="TASK",
                request_id="retention-task",
                ip_address_hash="",
                response_status=200,
                processing_time_ms=0,
                record_id=None,
                error_code=f"deleted:{deleted}",
                neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
            )
        )
        if db.scalars(
            select(ProvenanceRecord.record_id).where(
                ProvenanceRecord.created_at < archive_cutoff
            )
        ).first():
            db.add(
                create_audit_entry(
                    event_type="retention.archive_intent",
                    tenant_id=None,
                    api_key_hash="",
                    endpoint="/system/retention",
                    method="TASK",
                    request_id="retention-task",
                    ip_address_hash="",
                    response_status=200,
                    processing_time_ms=0,
                    record_id=None,
                    error_code="cold_storage_stub",
                    neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
                )
            )
        db.commit()
    return deleted


async def retention_loop() -> None:
    while True:
        now = now_utc()
        next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        await asyncio.sleep((next_run - now).total_seconds())
        await enforce_retention_policy()
