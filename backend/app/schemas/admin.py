"""Schemas API — Admin Center."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class AdminAccessResponse(BaseModel):
    can_view: bool
    can_mutate: bool
    role: str
    permissions: list[str]


class AdminUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    role: str
    roles: list[str] = Field(default_factory=list)
    department: str | None = None
    supervisor_id: uuid.UUID | None = None
    supervisor_name: str | None = None
    visible_company_ids: list[int] = Field(default_factory=list)
    odoo_user_id: int | None = None
    m365_prepared: bool = False
    m365_connection_status: str | None = None
    open_tasks_count: int = 0
    created_at: datetime | None = None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int


class AdminUserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=8)
    role: str | None = None
    roles: list[str] | None = None
    department: str | None = None
    supervisor_id: uuid.UUID | None = None
    visible_company_ids: list[int] = Field(default_factory=list)
    odoo_user_id: int | None = None
    is_active: bool = True


class AdminUserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8)
    role: str | None = None
    roles: list[str] | None = None
    department: str | None = None
    supervisor_id: uuid.UUID | None = None
    visible_company_ids: list[int] | None = None
    odoo_user_id: int | None = None
    is_active: bool | None = None


class AdminUserStatusRequest(BaseModel):
    is_active: bool


class AdminUserStatusResponse(BaseModel):
    id: uuid.UUID
    is_active: bool
    open_tasks_count: int = 0
    message: str


class AdminResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)


class AdminResetPasswordResponse(BaseModel):
    id: uuid.UUID
    message: str


class AdminUserRolesRequest(BaseModel):
    roles: list[str] = Field(min_length=1)


class AdminUserRolesResponse(BaseModel):
    id: uuid.UUID
    role: str
    roles: list[str]
    message: str


class RoleInfoResponse(BaseModel):
    key: str
    label: str
    permissions: list[str]


class RoleListResponse(BaseModel):
    items: list[RoleInfoResponse]


class TenantModuleResponse(BaseModel):
    module_key: str
    name: str
    is_enabled: bool
    is_future: bool


class TenantModuleListResponse(BaseModel):
    items: list[TenantModuleResponse]


class TenantModuleUpdateRequest(BaseModel):
    is_enabled: bool


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    is_active: bool


class DepartmentListResponse(BaseModel):
    items: list[DepartmentResponse]


class DepartmentCreateRequest(BaseModel):
    key: str
    name: str


class DepartmentUpdateRequest(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class RoutingRuleAdminResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    name: str
    category: str
    department: str
    default_priority: str
    default_assignee_name: str | None
    default_assignee_id: uuid.UUID | None
    default_supervisor_name: str | None
    default_supervisor_id: uuid.UUID | None
    due_hours: int | None
    notification_message: str | None
    checklist_template: list[str] = Field(default_factory=list)
    is_active: bool


class RoutingRuleListResponse(BaseModel):
    items: list[RoutingRuleAdminResponse]


class RoutingRuleUpdateRequest(BaseModel):
    name: str | None = None
    default_priority: str | None = None
    default_assignee_name: str | None = None
    default_assignee_id: uuid.UUID | None = None
    default_supervisor_name: str | None = None
    default_supervisor_id: uuid.UUID | None = None
    due_hours: int | None = None
    notification_message: str | None = None
    checklist_template: list[str] | None = None
    is_active: bool | None = None


class TenantSettingsResponse(BaseModel):
    language: str
    timezone: str
    default_currency: str
    primary_company: str | None
    qa_policies_visible: bool
    integration_status: dict[str, Any] = Field(default_factory=dict)
