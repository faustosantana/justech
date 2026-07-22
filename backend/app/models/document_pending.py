"""Pendientes documentales detectados automáticamente por JAIOS."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentPendingItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_pending_items"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    company_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("licitador_company_profiles.id", ondelete="SET NULL"), index=True
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, default="document")
    item_key: Mapped[str] = mapped_column(String(128), nullable=False)
    item_label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="missing")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_to_email: Mapped[str | None] = mapped_column(String(255))
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reminder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onedrive_path: Mapped[str | None] = mapped_column(Text)
    onedrive_url: Mapped[str | None] = mapped_column(Text)
    suggested_filename: Mapped[str | None] = mapped_column(String(512))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(32), default="auto", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class CompanyProfileFormToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "company_profile_form_tokens"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("licitador_company_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
