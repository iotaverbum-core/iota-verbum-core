from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from iota_verbum_api.db.models import DocumentInput, ProvenanceRecord
from iota_verbum_api.utils import now_utc, sha256_text


def next_record_id(document_hash: str) -> str:
    return f"prv_{document_hash[:12]}{uuid.uuid4().hex[:12]}"


def append_record_audit_log(existing: list, *, event: str, tenant_id: str) -> list:
    return [
        *(existing or []),
        {
            "event": event,
            "timestamp": now_utc().replace(microsecond=0).isoformat().replace(
                "+00:00", "Z"
            ),
            "tenant_id": tenant_id,
        },
    ]


def write_provenance_record(
    db: Session,
    *,
    record_id: str,
    tenant_id: str,
    domain: str,
    language_detected: str,
    extraction_result: dict,
    governance_metadata: dict,
    neurosymbolic_boundary: str,
    raw_text: str,
    input_format: str,
    pdf_metadata: dict | None,
    language_detection_metadata: dict | None,
    extraction_language: str,
    rule_set_version: str,
) -> ProvenanceRecord:
    document_hash = sha256_text(raw_text)
    record = ProvenanceRecord(
        record_id=record_id,
        document_hash=document_hash,
        tenant_id=tenant_id,
        domain=domain,
        language_detected=language_detected,
        extraction_result=extraction_result,
        governance_metadata=governance_metadata,
        neurosymbolic_boundary=neurosymbolic_boundary,
        audit_log=append_record_audit_log([], event="create", tenant_id=tenant_id),
        input_format=input_format,
        pdf_metadata=pdf_metadata,
        language_detection_metadata=language_detection_metadata,
        extraction_language=extraction_language,
        rule_set_version=rule_set_version,
    )
    db.add(record)
    db.add(DocumentInput(record_id=record_id, tenant_id=tenant_id, raw_text=raw_text))
    return record


def load_record(db: Session, record_id: str, tenant_id: str) -> ProvenanceRecord | None:
    stmt = select(ProvenanceRecord).where(
        ProvenanceRecord.record_id == record_id,
        ProvenanceRecord.tenant_id == tenant_id,
    )
    return db.scalar(stmt)


def load_document_input(
    db: Session, record_id: str, tenant_id: str
) -> DocumentInput | None:
    stmt = select(DocumentInput).where(
        DocumentInput.record_id == record_id,
        DocumentInput.tenant_id == tenant_id,
    )
    return db.scalar(stmt)
