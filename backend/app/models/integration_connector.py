"""Conectores dinámicos configurables desde UI."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class IntegrationProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_providers"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_integration_provider_slug"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(32), default="rest_api", nullable=False)
    auth_method: Mapped[str] = mapped_column(String(32), default="api_key", nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    secrets_encrypted: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_link_mode: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    documentation: Mapped[str | None] = mapped_column(Text, nullable=True)
    read_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    environment: Mapped[str] = mapped_column(String(16), default="development", nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_test_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class IntegrationCredential(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_credentials"
    __table_args__ = (UniqueConstraint("provider_id", "credential_key", name="uq_integration_credential_key"),)

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_providers.id", ondelete="CASCADE"), nullable=False
    )
    credential_key: Mapped[str] = mapped_column(String(64), nullable=False)
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IntegrationEndpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_endpoints"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    http_method: Mapped[str] = mapped_column(String(8), default="GET", nullable=False)
    query_params: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    body_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    headers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    response_hint: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    transform: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    assistant_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class IntegrationUserLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_user_links"
    __table_args__ = (UniqueConstraint("provider_id", "user_id", name="uq_integration_user_link"),)

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_providers.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    external_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_account_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="linked", nullable=False)
    permissions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    link_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class IntegrationTestLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_test_logs"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_endpoints.id", ondelete="SET NULL"), nullable=True
    )
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    tested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IntegrationAuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_audit_logs"

    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_providers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
