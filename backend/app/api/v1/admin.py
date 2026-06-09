"""API — Centro de Administración."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request

from app.api.deps import AdminMutator, AdminViewer, CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.admin import (
    AdminAccessResponse,
    AdminUserCreateRequest,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdateRequest,
    RoleListResponse,
    RoutingRuleAdminResponse,
    RoutingRuleListResponse,
    RoutingRuleUpdateRequest,
    TenantModuleListResponse,
    TenantModuleResponse,
    TenantModuleUpdateRequest,
    TenantSettingsResponse,
)
from app.services.admin_service import AdminService
from app.core.exceptions import JAIOSException
from app.schemas.company_context import UserCompaniesAdminResponse, UserCompaniesAdminUpdate
from app.services.global_company_context_service import GlobalCompanyContextService

router = APIRouter(prefix="/admin", tags=["Centro de Administración"])


def _svc(db: DbSession, user: CurrentUser) -> AdminService:
    ctx = require_tenant_context()
    return AdminService(db, ctx.tenant_id, actor_id=user.id)


@router.get("/access", response_model=AdminAccessResponse)
async def admin_access(db: DbSession, user: CurrentUser, _: TenantCtx) -> AdminAccessResponse:
    return await _svc(db, user).access_info(user)


@router.get("/users", response_model=AdminUserListResponse)
async def list_admin_users(db: DbSession, user: AdminViewer, _: TenantCtx) -> AdminUserListResponse:
    return await _svc(db, user).list_users()


@router.post("/users", response_model=AdminUserResponse, status_code=201)
async def create_admin_user(
    db: DbSession, user: AdminMutator, _: TenantCtx, payload: AdminUserCreateRequest
) -> AdminUserResponse:
    try:
        created = await _svc(db, user).create_user(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return created


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_admin_user(
    db: DbSession,
    user: AdminMutator,
    _: TenantCtx,
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
) -> AdminUserResponse:
    updated = await _svc(db, user).update_user(user_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return updated


@router.post("/users/{user_id}/disable", status_code=204)
async def disable_admin_user(
    db: DbSession, user: AdminMutator, _: TenantCtx, user_id: uuid.UUID
) -> None:
    if not await _svc(db, user).disable_user(user_id):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")


@router.get("/users/{user_id}/companies", response_model=UserCompaniesAdminResponse)
async def admin_get_user_companies(
    db: DbSession, user: AdminViewer, _: TenantCtx, user_id: uuid.UUID
) -> UserCompaniesAdminResponse:
    ctx = require_tenant_context()
    try:
        return await GlobalCompanyContextService(db, ctx.tenant_id, user_id).admin_get_user_companies(
            user_id
        )
    except JAIOSException as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.put("/users/{user_id}/companies", response_model=UserCompaniesAdminResponse)
async def admin_set_user_companies(
    db: DbSession,
    user: AdminMutator,
    _: TenantCtx,
    user_id: uuid.UUID,
    payload: UserCompaniesAdminUpdate,
) -> UserCompaniesAdminResponse:
    ctx = require_tenant_context()
    try:
        return await GlobalCompanyContextService(db, ctx.tenant_id, user.id).admin_set_user_companies(
            user_id, payload
        )
    except JAIOSException as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get("/roles", response_model=RoleListResponse)
async def list_roles(db: DbSession, user: AdminViewer, _: TenantCtx) -> RoleListResponse:
    return await _svc(db, user).list_roles()


@router.get("/modules", response_model=TenantModuleListResponse)
async def list_modules(db: DbSession, user: AdminViewer, _: TenantCtx) -> TenantModuleListResponse:
    return await _svc(db, user).list_modules()


@router.put("/modules/{module_key}", response_model=TenantModuleResponse)
async def update_module(
    db: DbSession,
    user: AdminMutator,
    _: TenantCtx,
    module_key: str,
    payload: TenantModuleUpdateRequest,
) -> TenantModuleResponse:
    updated = await _svc(db, user).update_module(module_key, payload.is_enabled)
    if not updated:
        raise HTTPException(status_code=404, detail="Módulo no encontrado")
    return updated


@router.get("/departments", response_model=DepartmentListResponse)
async def list_departments(db: DbSession, user: AdminViewer, _: TenantCtx) -> DepartmentListResponse:
    return await _svc(db, user).list_departments()


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    db: DbSession, user: AdminMutator, _: TenantCtx, payload: DepartmentCreateRequest
) -> DepartmentResponse:
    return await _svc(db, user).create_department(payload)


@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    db: DbSession,
    user: AdminMutator,
    _: TenantCtx,
    dept_id: uuid.UUID,
    payload: DepartmentUpdateRequest,
) -> DepartmentResponse:
    updated = await _svc(db, user).update_department(dept_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return updated


@router.get("/routing-rules", response_model=RoutingRuleListResponse)
async def list_routing_rules(
    db: DbSession, user: AdminViewer, _: TenantCtx
) -> RoutingRuleListResponse:
    return await _svc(db, user).list_routing_rules()


@router.put("/routing-rules/{rule_id}", response_model=RoutingRuleAdminResponse)
async def update_routing_rule(
    db: DbSession,
    user: AdminMutator,
    _: TenantCtx,
    rule_id: uuid.UUID,
    payload: RoutingRuleUpdateRequest,
) -> RoutingRuleAdminResponse:
    updated = await _svc(db, user).update_routing_rule(rule_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return updated


@router.get("/settings", response_model=TenantSettingsResponse)
async def get_admin_settings(
    db: DbSession, user: AdminViewer, _: TenantCtx
) -> TenantSettingsResponse:
    return await _svc(db, user).get_settings()
