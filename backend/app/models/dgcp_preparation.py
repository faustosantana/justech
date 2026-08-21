"""Checklist operativo de preparación de licitaciones (JAIOS — no Odoo).

Separado del checklist documental (ProcessRequirement / bid_package JSONB).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DGCPChecklistTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dgcp_checklist_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class DGCPChecklistTemplateItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dgcp_checklist_template_items"
    __table_args__ = (
        UniqueConstraint("template_id", "item_key", name="uq_dgcp_checklist_tpl_item_key"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dgcp_checklist_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_offset_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DGCPPreparationTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dgcp_preparation_tasks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending | in_progress | completed | not_applicable
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    # high | medium | low
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    template_item_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class DGCPPrepAlertLog(UUIDPrimaryKeyMixin, Base):
    """Dedup de alertas: user + tender + task + alert_type + deadline."""

    __tablename__ = "dgcp_prep_alert_logs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dedup_key", name="uq_dgcp_prep_alert_dedup"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dedup_key: Mapped[str] = mapped_column(String(320), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    deadline_key: Mapped[str] = mapped_column(String(64), nullable=False)
    notification_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
