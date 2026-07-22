"""Modelo — process_requirements (Fase 1 expediente / requisitos del proceso)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

APPROVED_STATUSES = frozenset({
    "pending",
    "detected",
    "associated",
    "needs_review",
    "valid",
    "expired",
    "not_applicable",
    "completed",
})


class ProcessRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "process_requirements"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_key: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    document_ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    document_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    template_ref: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    autofill_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    autofill_last_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    legacy_checklist_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
