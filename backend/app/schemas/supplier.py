"""Schemas — Directorio inteligente de proveedores."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

SUPPLIER_TYPE_PATTERN = (
    "^(proveedor|fabricante|mayorista|distribuidor|cliente|aliado|"
    "subcontratista|transportista|tecnico_externo|competidor)$"
)
SUPPLIER_STATUS_PATTERN = "^(activo|inactivo|preferido|bloqueado)$"


class SupplierCategoryBase(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    slug: str | None = None
    description: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    parent_id: uuid.UUID | None = None
    is_active: bool = True


class SupplierCategoryCreate(SupplierCategoryBase):
    pass


class SupplierCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=128)
    slug: str | None = None
    description: str | None = None
    synonyms: list[str] | None = None
    parent_id: uuid.UUID | None = None
    is_active: bool | None = None


class SupplierCategoryResponse(SupplierCategoryBase):
    id: uuid.UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierCategoryListResponse(BaseModel):
    items: list[SupplierCategoryResponse]
    total: int


class SupplierContactResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    is_primary: bool = False

    model_config = {"from_attributes": True}


class SupplierInteractionResponse(BaseModel):
    id: uuid.UUID
    interaction_type: str
    channel: str
    subject: str | None = None
    body: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    document_type: str | None = None
    file_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierPriceListSummary(BaseModel):
    id: uuid.UUID
    price_list_file_id: uuid.UUID
    filename: str | None = None
    detected_brands: list[str] = Field(default_factory=list)
    detected_categories: list[str] = Field(default_factory=list)
    product_count: int = 0
    linked_at: datetime
    file_modified_at: datetime | None = None


class SupplierBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    legal_name: str | None = None
    company_type: str = Field(pattern=SUPPLIER_TYPE_PATTERN)
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    primary_contact: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    country: str | None = "República Dominicana"
    category: str | None = None
    primary_category_id: uuid.UUID | None = None
    category_ids: list[uuid.UUID] = Field(default_factory=list)
    subcategories: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    products_services: list[str] = Field(default_factory=list)
    payment_terms: str | None = None
    delivery_time: str | None = None
    currency: str | None = "DOP"
    commercial_terms: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: str = Field(default="activo", pattern=SUPPLIER_STATUS_PATTERN)
    internal_rating: Decimal | None = Field(default=None, ge=0, le=5)
    odoo_partner_id: int | None = None
    price_supplier_name: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    legal_name: str | None = None
    company_type: str | None = Field(default=None, pattern=SUPPLIER_TYPE_PATTERN)
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    primary_contact: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    country: str | None = None
    category: str | None = None
    primary_category_id: uuid.UUID | None = None
    category_ids: list[uuid.UUID] | None = None
    subcategories: list[str] | None = None
    brands: list[str] | None = None
    products_services: list[str] | None = None
    payment_terms: str | None = None
    delivery_time: str | None = None
    currency: str | None = None
    commercial_terms: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    status: str | None = Field(default=None, pattern=SUPPLIER_STATUS_PATTERN)
    internal_rating: Decimal | None = Field(default=None, ge=0, le=5)
    odoo_partner_id: int | None = None
    price_supplier_name: str | None = None


class SupplierResponse(SupplierBase):
    id: uuid.UUID
    last_purchase_at: datetime | None = None
    last_quote_at: datetime | None = None
    categories: list[SupplierCategoryResponse] = Field(default_factory=list)
    price_lists_count: int = 0
    products_indexed_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    total: int


class SupplierDashboardStats(BaseModel):
    total_suppliers: int
    active_suppliers: int
    preferred_suppliers: int
    by_type: dict[str, int]
    by_category: list[dict[str, str | int]]


class SupplierSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    company_type: str | None = None
    category_id: uuid.UUID | None = None
    brand: str | None = None
    status: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class SupplierSearchMatch(BaseModel):
    supplier: SupplierResponse
    score: float
    matched_terms: list[str] = Field(default_factory=list)
    matched_categories: list[str] = Field(default_factory=list)
    matched_brands: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    recommendation_reason: str | None = None


class SupplierSearchResponse(BaseModel):
    query: str
    interpreted_categories: list[str] = Field(default_factory=list)
    interpreted_brands: list[str] = Field(default_factory=list)
    results: list[SupplierSearchMatch]
    total: int


class SupplierImportRequest(BaseModel):
    source: str = Field(pattern="^(csv|excel|outlook|email|whatsapp|price_list|onedrive)$")
    dry_run: bool = False
    rows: list[dict] = Field(default_factory=list)


class SupplierImportResponse(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)


class SupplierQuoteRequest(BaseModel):
    subject: str | None = None
    message: str | None = None
    products: list[str] = Field(default_factory=list)
    channel: str = Field(default="email", pattern="^(email|whatsapp|both)$")


class SupplierQuoteResponse(BaseModel):
    supplier_id: uuid.UUID
    subject: str
    email_body: str | None = None
    whatsapp_message: str | None = None
    interaction_id: uuid.UUID | None = None


class SupplierTenderSuggestionRequest(BaseModel):
    requirements: list[str] = Field(default_factory=list)
    description: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class SupplierTenderSuggestion(BaseModel):
    supplier: SupplierResponse
    score: float
    matched_requirements: list[str] = Field(default_factory=list)
    has_price_list: bool = False
    last_quote_at: datetime | None = None


class SupplierTenderSuggestionResponse(BaseModel):
    requirements: list[str]
    suggestions: list[SupplierTenderSuggestion]
