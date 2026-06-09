"""Schemas — Price Intelligence Engine v2."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PriceProductResponse(BaseModel):
    id: UUID
    supplier: str | None
    manufacturer: str | None
    brand: str | None
    sku: str | None
    mpn: str | None
    model: str | None
    description: str | None
    category: str | None
    product_type: str
    excluded_from_laptop: bool = True
    is_cotizable: bool = False
    price_review_status: str = "ok"
    classification_label: str = "producto general"
    stock_source_column: str | None = None
    processor: str | None
    ram_gb: int | None
    storage_gb: int | None
    storage_type: str | None
    display: str | None
    operating_system: str | None
    price: Decimal | None
    preferred_price: Decimal | None = None
    preferred_price_field: str | None = None
    price_regular: Decimal | None = None
    price_rebate: Decimal | None = None
    price_discount: Decimal | None = None
    prices_original: dict = Field(default_factory=dict)
    currency: str
    stock: int | None
    in_transit: int | None
    stock_text_original: str | None = None
    warranty: str | None
    source_filename: str
    source_sheet: str | None
    source_row: int | None
    source_file_date: datetime | None = None
    source_file_date_estimated: bool = True
    file_id: UUID
    indexed_at: datetime

    model_config = {"from_attributes": True}


class PriceProductDetailResponse(PriceProductResponse):
    raw_row_json: dict = Field(default_factory=dict)
    raw_columns_json: list = Field(default_factory=list)
    comparison_price_label: str = "Precio usado para comparación"
    cotizable_warning: str | None = None


class PriceSearchResponse(BaseModel):
    query: str | None = None
    total: int
    items: list[PriceProductResponse]


class PriceCompareAlternative(BaseModel):
    supplier: str | None
    brand: str | None
    description: str | None
    sku: str | None
    price: Decimal | None
    preferred_price: Decimal | None = None
    currency: str
    stock: int | None
    source_filename: str
    source_sheet: str | None
    source_row: int | None = None
    file_date: datetime | None
    file_date_estimated: bool = True


class PriceCompareResponse(BaseModel):
    question: str
    best_supplier: str | None
    best_product: PriceProductResponse | None
    alternatives: list[PriceCompareAlternative] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str


class PriceSyncResponse(BaseModel):
    files_detected: int
    files_new: int
    files_unchanged: int
    files_updated: int
    records_created: int
    duration_ms: int
    errors: list[str] = Field(default_factory=list)


class PriceQuoteDraftCreate(BaseModel):
    product_id: UUID
    client_name: str | None = None
    quantity: int = Field(default=1, ge=1)
    margin_percent: Decimal | None = Field(default=Decimal("15"), ge=0, le=500)


class PriceQuoteDraftResponse(BaseModel):
    id: UUID
    product_id: UUID
    task_id: UUID | None = None
    client_name: str | None
    quantity: int
    description: str | None
    cost_price: Decimal | None
    currency: str
    supplier: str | None
    margin_percent: Decimal | None
    sale_price_suggested: Decimal | None
    source_filename: str | None
    source_sheet: str | None
    source_row: int | None
    source_file_date: datetime | None
    status: str
    odoo_product_id: int | None
    odoo_match_status: str | None
    user_id: UUID | None = None
    copy_line: str | None = None

    model_config = {"from_attributes": True}


class PriceQuoteDraftListResponse(BaseModel):
    items: list[PriceQuoteDraftResponse]
    total: int


class OdooProductMatchResponse(BaseModel):
    found: bool
    product_id: int | None = None
    product_name: str | None = None
    message: str
    action: str = "none"
    odoo_default_code: str | None = None
