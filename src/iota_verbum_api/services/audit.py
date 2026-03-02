from __future__ import annotations

from sqlalchemy.orm import Session

from iota_verbum_api.db.models import AuditLog


def create_audit_entry(
    *,
    event_type: str,
    tenant_id: str | None,
    api_key_hash: str,
    endpoint: str,
    method: str,
    request_id: str,
    ip_address_hash: str,
    response_status: int,
    processing_time_ms: int,
    record_id: str | None,
    error_code: str | None,
    neurosymbolic_boundary: str | None,
) -> AuditLog:
    return AuditLog(
        event_type=event_type,
        tenant_id=tenant_id,
        api_key_hash=api_key_hash,
        endpoint=endpoint,
        method=method,
        request_id=request_id,
        ip_address_hash=ip_address_hash,
        response_status=response_status,
        processing_time_ms=processing_time_ms,
        record_id=record_id,
        error_code=error_code,
        neurosymbolic_boundary=neurosymbolic_boundary,
    )


def insert_audit_entry(db: Session, entry: AuditLog) -> None:
    db.add(entry)
