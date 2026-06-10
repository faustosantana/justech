"""Registro de PDFs finales firmados/sellados para expediente DGCP."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentFinalizationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_finalization_records"
    __table_args__ = {"schema": "jaios"}

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    checklist_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    company_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_process_documents.id", ondelete="SET NULL"), nullable=True
    )
    source_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    signature_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stamp_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    output_storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False, default="pdf_final_generado")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
