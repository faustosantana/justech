"""Schemas — Empresas y proveedores."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BusinessCompanyBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    company_type: str = Field(
        pattern="^(proveedor|fabricante|mayorista|distribuidor|cliente|aliado|"
        "subcontratista|transportista|tecnico_externo|competidor)$"
    )
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    primary_contact: str | None = None
    website: str | None = None
    category: str | None = None
    brands: list[str] = Field(default_factory=list)
    commercial_terms: str | None = None
    notes: str | None = None
    status: str = Field(default="activo", pattern="^(activo|inactivo|preferido|bloqueado)$")
    odoo_partner_id: int | None = None
    price_supplier_name: str | None = None


class BusinessCompanyCreate(BusinessCompanyBase):
    pass


class BusinessCompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    company_type: str | None = Field(
        default=None,
        pattern="^(proveedor|fabricante|mayorista|distribuidor|cliente|aliado|"
        "subcontratista|transportista|tecnico_externo|competidor)$",
    )
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    primary_contact: str | None = None
    website: str | None = None
    category: str | None = None
    brands: list[str] | None = None
    commercial_terms: str | None = None
    notes: str | None = None
    status: str | None = Field(default=None, pattern="^(activo|inactivo|preferido|bloqueado)$")
    odoo_partner_id: int | None = None
    price_supplier_name: str | None = None


class BusinessCompanyResponse(BusinessCompanyBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BusinessCompanyListResponse(BaseModel):
    items: list[BusinessCompanyResponse]
    total: int
