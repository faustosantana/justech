"""Microsoft 365 Operativo — correos procesados, acciones y automatización."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class M365MonitoredMailbox(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "m365_monitored_mailboxes"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_process: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class M365ProcessedEmail(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "m365_processed_emails"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mailbox: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_message_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(255))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    body_preview: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    classification_confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extracted_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    relations: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    suggested_actions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    attachments: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    sharepoint_path: Mapped[str | None] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(String(32), default="processed", nullable=False)
    graph_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    demo_source: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hermes_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    related_dgcp_process_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dgcp_opportunities.id", ondelete="SET NULL")
    )
    related_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL")
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(8))


class M365EmailActionLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "m365_email_action_logs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("m365_processed_emails.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action_key: Mapped[str] = mapped_column(String(64), nullable=False)
    action_label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class M365AutomationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "m365_automation_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    n8n_workflow_id: Mapped[str | None] = mapped_column(String(128))
    n8n_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
