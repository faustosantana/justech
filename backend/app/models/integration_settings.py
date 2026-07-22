"""Configuración de integraciones almacenada por tenant (UI)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TenantIntegrationSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenant_integration_settings"
    __table_args__ = (UniqueConstraint("tenant_id", "provider", name="uq_tenant_integration_provider"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    secrets_encrypted: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_test_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class IntegrationRepositoryBinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_repository_bindings"
    __table_args__ = (UniqueConstraint("tenant_id", "folder_key", name="uq_integration_repo_folder"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="onedrive", nullable=False)
    graph_item_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    drive_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    folder_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    web_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    indexed_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    repository_type: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    company_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delta_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_interval_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
