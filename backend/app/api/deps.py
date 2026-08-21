import uuid
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_permissions import can_mutate_admin, can_view_admin, normalize_roles
from app.core.exceptions import forbidden, unauthorized
from app.core.permissions import PermissionContext, build_permission_context, evaluate_permission_requirement
from app.core.security import verify_access_token
from app.core.tenant import get_current_role, parse_tenant_header, require_tenant_context, set_tenant_context
from app.db.session import get_db
from app.models.tenant import TenantMembership
from app.models.user import User

PermissionAction = Literal["view", "mutate", "manage"]

security = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_optional(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    if not credentials:
        return None
    payload = verify_access_token(credentials.credentials)
    if not payload:
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError, KeyError):
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    # Invalidate tokens after password reset / deactivate credential bump.
    token_cv = payload.get("cv")
    user_cv = int(getattr(user, "credentials_version", 0) or 0)
    if token_cv is not None:
        try:
            if int(token_cv) != user_cv:
                return None
        except (TypeError, ValueError):
            return None
    elif user_cv > 0:
        return None
    return user


async def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if not user:
        raise unauthorized()
    return user


async def resolve_tenant_context(
    request: Request,
    db: DbSession,
    user: Annotated[User | None, Depends(get_current_user_optional)],
    tenant_id: uuid.UUID | None = Depends(parse_tenant_header),
) -> None:
    """Populate request-scoped tenant context from JWT + header."""
    jwt_tenant_id: uuid.UUID | None = None
    jwt_role: str | None = None
    jwt_user_id: uuid.UUID | None = None

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        payload = verify_access_token(auth_header[7:])
        if payload:
            jwt_user_id = uuid.UUID(payload["sub"])
            if payload.get("tenant_id"):
                jwt_tenant_id = uuid.UUID(payload["tenant_id"])
            jwt_role = payload.get("role")

    effective_tenant = tenant_id or jwt_tenant_id
    effective_user = user.id if user else jwt_user_id

    if effective_tenant and effective_user and not user:
        result = await db.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == effective_tenant,
                TenantMembership.user_id == effective_user,
            )
        )
        if not result.scalar_one_or_none():
            raise forbidden("No membership for this tenant")

    if tenant_id and jwt_tenant_id and tenant_id != jwt_tenant_id and user and not user.is_superadmin:
        raise forbidden("Tenant mismatch between token and header")

    set_tenant_context(
        tenant_id=effective_tenant,
        user_id=effective_user,
        role=jwt_role,
    )


TenantCtx = Annotated[None, Depends(resolve_tenant_context)]


async def _membership_roles(db: AsyncSession, tenant_id: uuid.UUID | None, user_id: uuid.UUID) -> list[str] | None:
    if not tenant_id:
        return None
    result = await db.execute(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        return None
    return normalize_roles(list(getattr(membership, "roles", None) or []), fallback=membership.role)


async def require_admin_viewer(
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    _: TenantCtx,
) -> User:
    ctx = require_tenant_context()
    roles = await _membership_roles(db, ctx.tenant_id, user.id)
    if not can_view_admin(get_current_role(), user.is_superadmin, roles=roles):
        raise forbidden("Acceso restringido al Centro de Administración")
    return user


async def require_admin_mutator(
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    _: TenantCtx,
) -> User:
    ctx = require_tenant_context()
    roles = await _membership_roles(db, ctx.tenant_id, user.id)
    if not can_mutate_admin(get_current_role(), user.is_superadmin, roles=roles):
        raise forbidden("Permisos insuficientes para modificar administración")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminViewer = Annotated[User, Depends(require_admin_viewer)]
AdminMutator = Annotated[User, Depends(require_admin_mutator)]


def RequirePermission(
    *permissions: str,
    module: str | None = None,
    action: PermissionAction = "view",
    require_all: bool = True,
    company_param: str | None = None,
) -> Callable:
    async def _require_permission(
        request: Request,
        user: Annotated[User, Depends(get_current_user)],
        db: DbSession,
        _: TenantCtx,
    ) -> PermissionContext:
        company_key: str | None = None
        if company_param:
            raw = request.path_params.get(company_param) or request.query_params.get(company_param)
            if raw is not None:
                company_key = str(raw)

        ctx = await build_permission_context(db, user)
        allowed, _reason, message = await evaluate_permission_requirement(
            db,
            ctx,
            permissions=permissions,
            module=module,
            action=action,
            require_all=require_all,
            company_key=company_key,
        )
        if not allowed:
            raise forbidden(message)
        return ctx

    return _require_permission


RequireViewDgcp = Annotated[PermissionContext, Depends(RequirePermission("view_dgcp"))]
RequireViewOdoo = Annotated[PermissionContext, Depends(RequirePermission("view_odoo"))]
RequireViewM365 = Annotated[PermissionContext, Depends(RequirePermission("view_m365"))]
RequireViewPrices = Annotated[PermissionContext, Depends(RequirePermission(module="prices"))]
RequireViewSuppliers = Annotated[PermissionContext, Depends(RequirePermission(module="suppliers"))]
