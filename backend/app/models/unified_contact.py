"""Contactos unificados — perfil 360 empresarial."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UnifiedContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "unified_contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "normalized_key", name="uq_unified_contacts_tenant_key"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    primary_email: Mapped[str | None] = mapped_column(String(255), index=True)
    primary_phone: Mapped[str | None] = mapped_column(String(32), index=True)
    normalized_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UnifiedContactIdentity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "unified_contact_identities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source", "external_id", name="uq_unified_contact_identities_source"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unified_contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    company_name: Mapped[str | None] = mapped_column(String(255))
    profile_url: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
