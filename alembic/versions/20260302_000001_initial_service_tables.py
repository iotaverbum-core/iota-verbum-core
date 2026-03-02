from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260302_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provenance_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("record_id", sa.String(length=64), nullable=False),
        sa.Column("document_hash", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("language_detected", sa.String(length=8), nullable=False),
        sa.Column("extraction_result", sa.JSON(), nullable=False),
        sa.Column("governance_metadata", sa.JSON(), nullable=False),
        sa.Column("neurosymbolic_boundary", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_count", sa.Integer(), nullable=False),
        sa.Column("audit_log", sa.JSON(), nullable=False),
        sa.Column("input_format", sa.String(length=16), nullable=False),
        sa.Column("pdf_metadata", sa.JSON(), nullable=True),
        sa.Column("language_detection_metadata", sa.JSON(), nullable=True),
        sa.Column("extraction_language", sa.String(length=8), nullable=True),
        sa.Column("rule_set_version", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id"),
    )
    op.create_index(
        "idx_provenance_record_id", "provenance_records", ["record_id"], unique=False
    )
    op.create_index(
        "idx_provenance_tenant", "provenance_records", ["tenant_id"], unique=False
    )
    op.create_index(
        "idx_provenance_created", "provenance_records", ["created_at"], unique=False
    )

    op.create_table(
        "document_inputs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("record_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["record_id"], ["provenance_records.record_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", name="uq_document_inputs_record_id"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("method", sa.String(length=8), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("ip_address_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False),
        sa.Column("record_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("neurosymbolic_boundary", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_timestamp", "audit_log", ["timestamp"], unique=False)
    op.create_index("idx_audit_tenant", "audit_log", ["tenant_id"], unique=False)
    op.create_index("idx_audit_event", "audit_log", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_audit_event", table_name="audit_log")
    op.drop_index("idx_audit_tenant", table_name="audit_log")
    op.drop_index("idx_audit_timestamp", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("document_inputs")
    op.drop_index("idx_provenance_created", table_name="provenance_records")
    op.drop_index("idx_provenance_tenant", table_name="provenance_records")
    op.drop_index("idx_provenance_record_id", table_name="provenance_records")
    op.drop_table("provenance_records")
