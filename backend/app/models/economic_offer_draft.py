"""Borrador interno de oferta económica DGCP — pendiente de cotización Odoo."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class EconomicOfferDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "economic_offer_drafts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "opportunity_id",
            "requirement_id",
            name="uq_economic_offer_draft_opportunity_requirement",
        ),
        {"schema": "jaios"},
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    customer_name: Mapped[str | None] = mapped_column(String(255))
    odoo_partner_match_id: Mapped[int | None] = mapped_column(Integer)
    suggested_products: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="DOP")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    odoo_quotation_id: Mapped[int | None] = mapped_column(Integer)
    odoo_quotation_name: Mapped[str | None] = mapped_column(String(64))
    process_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_process_documents.id", ondelete="SET NULL")
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    attached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
