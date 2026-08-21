"""Histórico de adjudicaciones DGCP indexado."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DGCPHistoricalAward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dgcp_historical_awards"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "process_code",
            "contract_code",
            "item_description_user",
            name="uq_dgcp_hist_award_line",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    process_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    contract_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    buyer_institution: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    buyer_institution_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    award_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contract_object: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_description_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    supplier_rpe: Mapped[str | None] = mapped_column(String(64), nullable=True)
    awarded_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="DOP", nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_line_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    unit_measure: Mapped[str | None] = mapped_column(String(64), nullable=True)
    modality: Mapped[str | None] = mapped_column(String(128), nullable=True)
    objeto_proceso: Mapped[str | None] = mapped_column(String(128), nullable=True)
    award_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    process_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="dgcp_contratos", nullable=False)
    unspsc_family: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unspsc_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unspsc_subclass: Mapped[str | None] = mapped_column(String(32), nullable=True)
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DGCPHistoricalIndexJob(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dgcp_historical_index_jobs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # SUCCESS | FAILED | TIMEOUT | COMPLETED_AFTER_TIMEOUT | SOURCE_UNAVAILABLE | running | completed | failed
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    pages_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contracts_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_indexed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Completion marker / observability (nullable for legacy rows)
    rows_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result_meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class DGCPHistoricalIdentityAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Auditoría reversible de merges / keep-separate / ignore (sin borrar histórico)."""

    __tablename__ = "dgcp_historical_identity_actions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    party_type: Mapped[str] = mapped_column(String(16), nullable=False)  # supplier | institution
    identity_a: Mapped[str] = mapped_column(String(256), nullable=False)
    identity_b: Mapped[str] = mapped_column(String(256), nullable=False)
    canonical_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # merge | keep_separate | ignore | unmerge
    criterion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active | reversed
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
