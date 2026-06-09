"""Modelo — DGCP Bid Package (Fase 7.1)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DGCPBidPackage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dgcp_bid_packages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirements: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    checklist: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    bid_package: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    document_matches: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    requirement_risks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expediente_status: Mapped[str] = mapped_column(String(64), nullable=False, default="sin_preparar")
    expediente_path: Mapped[str | None] = mapped_column(Text)
    user_input: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    alerts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    generated_forms: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    requirement_evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    process_documents_summary: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
