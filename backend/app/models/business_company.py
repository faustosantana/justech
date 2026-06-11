"""Empresas y proveedores — directorio comercial JAIOS."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

COMPANY_TYPES = (
    "proveedor",
    "fabricante",
    "mayorista",
    "distribuidor",
    "cliente",
    "aliado",
    "subcontratista",
    "transportista",
    "tecnico_externo",
    "competidor",
)

COMPANY_STATUSES = (
    "activo",
    "inactivo",
    "preferido",
    "bloqueado",
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
    legal_name: Mapped[str | None] = mapped_column(String(255))
    whatsapp: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(128))
    province: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(64), default="República Dominicana")
    payment_terms: Mapped[str | None] = mapped_column(String(255))
    delivery_time: Mapped[str | None] = mapped_column(String(128))
    currency: Mapped[str | None] = mapped_column(String(8), default="DOP")
    products_services: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)
    subcategories: Mapped[list[str]] = mapped_column(ARRAY(String(128)), default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list)
    internal_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    last_purchase_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_quote_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    primary_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_categories.id", ondelete="SET NULL")
    )
