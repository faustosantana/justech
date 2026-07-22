"""Schemas — dashboards Licitador (legales, plantillas, precios)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LegalDocumentItem(BaseModel):
    id: str
    name: str
    document_type: str
    vigency_status: str = "sin_fecha"
    valid_until: str | None = None
    web_url: str | None = None
    source: str = "knowledge"


class CompanyLegalSummary(BaseModel):
    company_key: str
    company_label: str
    completeness_score: int = 0
    missing_profile_fields: list[str] = Field(default_factory=list)
    documents: list[LegalDocumentItem] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    expired_documents: list[str] = Field(default_factory=list)
    upcoming_documents: list[str] = Field(default_factory=list)


class LegalDocumentsDashboardResponse(BaseModel):
    companies: list[CompanyLegalSummary] = Field(default_factory=list)
    total_documents: int = 0
    total_expired: int = 0
    total_missing: int = 0


class DgcpTemplateItem(BaseModel):
    id: str
    name: str
    source: str
    document_category: str | None = None
    mime_type: str | None = None
    template_type: str | None = None
    web_url: str | None = None
    parent_path: str = ""
    fillable_fields_estimate: int = 0


class DgcpTemplatesDashboardResponse(BaseModel):
    templates: list[DgcpTemplateItem] = Field(default_factory=list)
    total: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)


class PriceFileItem(BaseModel):
    id: str
    name: str
    supplier: str | None = None
    records: int = 0
    status: str
    indexed_at: str | None = None
    parent_path: str = ""


class PriceIntelligenceDashboardResponse(BaseModel):
    pending_files: list[PriceFileItem] = Field(default_factory=list)
    processed_files: list[PriceFileItem] = Field(default_factory=list)
    total_products: int = 0
    total_suppliers: int = 0
    lists_today: int = 0
    recent_errors: list[str] = Field(default_factory=list)
