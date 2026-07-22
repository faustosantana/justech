"""Schemas — Oferta económica DGCP + Odoo."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EconomicOfferSuggestedProduct(BaseModel):
    product_name: str
    supplier: str | None = None
    cost_price: Decimal | None = None
    currency: str = "USD"
    stock: float | None = None
    source: str | None = None
    source_date: str | None = None
    price_product_id: UUID | None = None


class AttachOdooQuotationRequest(BaseModel):
    odoo_quotation_id: int
    requirement_id: UUID | None = None
    notes: str | None = None


class CreateEconomicOfferDraftTaskRequest(BaseModel):
    customer_name: str | None = None
    suggested_products: list[EconomicOfferSuggestedProduct] = Field(default_factory=list)
    notes: str | None = None
    assigned_to: UUID | None = None
    requirement_id: UUID | None = None


class EconomicOfferStatusResponse(BaseModel):
    opportunity_id: UUID
    opportunity_code: str
    requirement_key: str = "oferta_economica"
    requirement_id: UUID | None = None
    checklist_status: str
    display_status: str
    is_compliant: bool
    has_odoo_quotation: bool
    odoo_quotation_id: int | None = None
    odoo_quotation_name: str | None = None
    process_document_id: UUID | None = None
    document_title: str | None = None
    preparation_pct: float = 0
    draft_status: str | None = None
    draft_id: UUID | None = None
    task_id: UUID | None = None
    suggested_products: list[EconomicOfferSuggestedProduct] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttachOdooQuotationResponse(BaseModel):
    opportunity_id: UUID
    checklist_item_id: UUID
    requirement_key: str
    odoo_quotation_id: int
    odoo_quotation_name: str
    process_document_id: UUID
    document_title: str
    filename: str
    preparation_pct: float
    expediente_status: str
    economic_offer_status: str
    draft_id: UUID | None = None
    checklist: Any = None
    bid_package: Any = None


class CreateEconomicOfferTaskResponse(BaseModel):
    task_id: UUID
    title: str
    created: bool
    existing: bool = False
    draft_id: UUID | None = None
