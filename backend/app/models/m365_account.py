"""Cuentas Microsoft 365 por usuario JAIOS (preparación — sin tokens reales)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class M365UserAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "m365_user_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "jaios_user_id", name="uq_m365_user_accounts_tenant_user"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jaios_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255))
    microsoft_user_id: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(255))
    connection_status: Mapped[str] = mapped_column(String(32), default="not_connected", nullable=False)
    connection_mode: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    imap_host: Mapped[str | None] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(default=993, nullable=False)
    imap_password_encrypted: Mapped[str | None] = mapped_column(Text)
    scopes_granted: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
