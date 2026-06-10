"""Entidades de conocimiento — resolución Fase 4."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeEntity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_entities"
    __table_args__ = {"schema": "jaios"}

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String(255)), nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="seed")
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
