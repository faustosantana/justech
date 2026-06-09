"""Empresas y proveedores — directorio comercial JAIOS."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

COMPANY_TYPES = (
    "proveedor",
    "fabricante",
    "cliente",
    "aliado",
    "competidor",
)


class BusinessCompany(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_companies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    primary_contact: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(512))
    category: Mapped[str | None] = mapped_column(String(128))
    brands: Mapped[list[str]] = mapped_column(ARRAY(String(128)), default=list)
    commercial_terms: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="activo", index=True)
    odoo_partner_id: Mapped[int | None] = mapped_column()
    price_supplier_name: Mapped[str | None] = mapped_column(String(255))
