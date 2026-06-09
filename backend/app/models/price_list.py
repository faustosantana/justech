"""Modelos — Price Intelligence Engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PriceListFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "price_list_files"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier: Mapped[str | None] = mapped_column(String(255))
    manufacturer: Mapped[str | None] = mapped_column(String(128))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    file_date_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    audit_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PriceListProduct(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "price_list_products"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_list_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    supplier: Mapped[str | None] = mapped_column(String(255))
    manufacturer: Mapped[str | None] = mapped_column(String(128))
    sku: Mapped[str | None] = mapped_column(String(128), index=True)
    mpn: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(128), index=True)
    product_type: Mapped[str] = mapped_column(String(32), nullable=False, default="general", index=True)
    brand: Mapped[str | None] = mapped_column(String(128), index=True)
    processor: Mapped[str | None] = mapped_column(String(128))
    ram_gb: Mapped[int | None] = mapped_column(Integer, index=True)
    storage_gb: Mapped[int | None] = mapped_column(Integer, index=True)
    storage_type: Mapped[str | None] = mapped_column(String(32))
    display: Mapped[str | None] = mapped_column(String(64))
    operating_system: Mapped[str | None] = mapped_column(String(128))
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    preferred_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), index=True)
    preferred_price_field: Mapped[str | None] = mapped_column(String(64))
    price_regular: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    price_rebate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    price_discount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    prices_original: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    stock: Mapped[int | None] = mapped_column(Integer)
    in_transit: Mapped[int | None] = mapped_column(Integer)
    stock_text_original: Mapped[str | None] = mapped_column(Text)
    warranty: Mapped[str | None] = mapped_column(String(128))
    raw_row_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    raw_columns_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    search_blob: Mapped[str | None] = mapped_column(Text)
    is_commercial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    excluded_from_laptop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    is_cotizable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    price_review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    classification_label: Mapped[str] = mapped_column(String(64), nullable=False, default="producto general")
    stock_source_column: Mapped[str | None] = mapped_column(String(64))
    source_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_sheet: Mapped[str | None] = mapped_column(String(128))
    source_row: Mapped[int | None] = mapped_column(Integer)
    source_file_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PriceQuoteDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "price_quote_drafts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("price_list_products.id", ondelete="CASCADE"), nullable=False
    )
    client_name: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(Text)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    supplier: Mapped[str | None] = mapped_column(String(255))
    margin_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    sale_price_suggested: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    source_filename: Mapped[str | None] = mapped_column(String(512))
    source_sheet: Mapped[str | None] = mapped_column(String(128))
    source_row: Mapped[int | None] = mapped_column(Integer)
    source_file_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    odoo_product_id: Mapped[int | None] = mapped_column(Integer)
    odoo_match_status: Mapped[str | None] = mapped_column(String(32))
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
