from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    record_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    language_detected: Mapped[str] = mapped_column(String(8), nullable=False)
    extraction_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    governance_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    neurosymbolic_boundary: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    verified_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    audit_log: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    input_format: Mapped[str] = mapped_column(String(16), default="text", nullable=False)
    pdf_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    language_detection_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extraction_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    rule_set_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    document_input: Mapped["DocumentInput"] = relationship(back_populates="provenance_record")


class DocumentInput(Base):
    __tablename__ = "document_inputs"
    __table_args__ = (UniqueConstraint("record_id", name="uq_document_inputs_record_id"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    record_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("provenance_records.record_id"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    provenance_record: Mapped[ProvenanceRecord] = relationship(back_populates="document_input")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(128), nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    neurosymbolic_boundary: Mapped[str | None] = mapped_column(String(32), nullable=True)

