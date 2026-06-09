"""Schemas — contexto global multiempresa."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CompanyOption(BaseModel):
    id: int
    name: str
    selected: bool = False


class GlobalCompanyContextResponse(BaseModel):
    selection_mode: str = "single"
    active_company_id: int | None = None
    active_company_name: str | None = None
    selected_company_ids: list[int] = Field(default_factory=list)
    selected_company_names: list[str] = Field(default_factory=list)
    allowed_companies: list[CompanyOption] = Field(default_factory=list)
    can_select_all: bool = False
    can_select_multiple: bool = True
    scope_label: str = "Sin empresa seleccionada"
    odoo_connected: bool = False


class GlobalCompanyContextUpdate(BaseModel):
    selection_mode: str = Field(pattern="^(single|multi|all)$")
    active_company_id: int | None = None
    selected_company_ids: list[int] = Field(default_factory=list)


class UserCompaniesAdminResponse(BaseModel):
    user_id: UUID
    visible_company_ids: list[int] = Field(default_factory=list)
    visible_company_names: list[str] = Field(default_factory=list)
    available_companies: list[CompanyOption] = Field(default_factory=list)
    default_company_id: int | None = None
    can_select_all: bool = False
    user_role: str | None = None
    odoo_allowed_company_ids: list[int] = Field(default_factory=list)


class UserCompaniesAdminUpdate(BaseModel):
    visible_company_ids: list[int] = Field(default_factory=list)
    can_select_all: bool | None = None
    default_company_id: int | None = None


class AllowedCompaniesResponse(BaseModel):
    items: list[CompanyOption]
    can_select_all: bool = False
    default_company_id: int | None = None
    updated_at: datetime | None = None
