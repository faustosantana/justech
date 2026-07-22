"""Perfiles de empresa para licitaciones — sincronizados desde OneDrive JSON."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LicitadorCompanyProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "licitador_company_profiles"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    razon_social: Mapped[str | None] = mapped_column(String(512))
    nombre_comercial: Mapped[str | None] = mapped_column(String(512))
    rnc: Mapped[str | None] = mapped_column(String(32))
    direccion: Mapped[str | None] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(String(64))
    correo: Mapped[str | None] = mapped_column(String(255))
    representante_legal: Mapped[str | None] = mapped_column(String(255))
    cedula_representante: Mapped[str | None] = mapped_column(String(32))
    cargo_representante: Mapped[str | None] = mapped_column(String(128))
    raw_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    missing_fields: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    graph_file_id: Mapped[str | None] = mapped_column(String(128))
    source_filename: Mapped[str | None] = mapped_column(String(512))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
