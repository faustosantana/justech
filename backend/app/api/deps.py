import uuid
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_permissions import can_mutate_admin, can_view_admin
from app.core.auth_trace import record_auth_reject
from app.core.exceptions import forbidden, unauthorized
from app.core.permissions import PermissionContext, build_permission_context, evaluate_permission_requirement
from app.core.security import classify_access_token, verify_access_token
from app.core.tenant import get_current_role, parse_tenant_header, require_tenant_context, set_tenant_context
from app.db.session import get_db
from app.models.tenant import TenantMembership
from app.models.user import User

PermissionAction = Literal["view", "mutate", "manage"]

security = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_optional(
    request: Request,
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    if not credentials:
        request.state.auth_reject_reason = "token_missing"
        request.state.auth_token_present = False
        return None
    payload, reason = classify_access_token(credentials.credentials)
    if not payload:
        request.state.auth_reject_reason = reason or "token_malformed"
        request.state.auth_token_present = True
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError, KeyError):
        request.state.auth_reject_reason = "subject_missing"
        request.state.auth_token_present = True
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        request.state.auth_reject_reason = "user_not_found"
        request.state.auth_subject = str(user_id)
        request.state.auth_token_present = True
        return None
    if not user.is_active:
        request.state.auth_reject_reason = "user_inactive"
        request.state.auth_subject = str(user_id)
        request.state.auth_token_present = True
        return None
    # Invalidate access tokens issued before password reset / credential bump.
    token_cv = payload.get("cv")
    user_cv = int(getattr(user, "credentials_version", 0) or 0)
    if token_cv is not None:
        try:
            if int(token_cv) != user_cv:
                request.state.auth_reject_reason = "credentials_stale"
                request.state.auth_subject = str(user_id)
                request.state.auth_token_present = True
                return None
        except (TypeError, ValueError):
            request.state.auth_reject_reason = "credentials_stale"
            request.state.auth_subject = str(user_id)
            request.state.auth_token_present = True
            return None
    elif user_cv > 0:
        # Tokens without cv issued before this hotfix: reject only after a reset bumped version.
        request.state.auth_reject_reason = "credentials_stale"
        request.state.auth_subject = str(user_id)
        request.state.auth_token_present = True
        return None
    request.state.auth_reject_reason = None
    request.state.auth_subject = str(user_id)
    request.state.auth_token_present = True
    return user


async def get_current_user(
    request: Request,
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if not user:
        reason = getattr(request.state, "auth_reject_reason", None) or "unknown_auth_error"
        record_auth_reject(
            reason=reason,
            path=getattr(request.url, "path", None),
            correlation_id=request.headers.get("X-Correlation-Id")
            or request.headers.get("X-Request-Id"),
            token_present=bool(getattr(request.state, "auth_token_present", False)),
            subject=getattr(request.state, "auth_subject", None),
            user_lookup=reason if reason in {"user_not_found", "user_inactive"} else None,
        )
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


async def require_admin_viewer(
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    _: TenantCtx,
) -> User:
    ctx = require_tenant_context()
    roles: list[str] | None = None
    if ctx.tenant_id:
        result = await db.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == ctx.tenant_id,
                TenantMembership.user_id == user.id,
            )
        )
        membership = result.scalar_one_or_none()
        if membership:
            from app.core.admin_permissions import normalize_roles

            roles = normalize_roles(
                list(getattr(membership, "roles", None) or []),
                fallback=membership.role,
            )
    if not can_view_admin(get_current_role(), user.is_superadmin, roles=roles):
        raise forbidden("Acceso restringido al Centro de Administración")
    return user


async def require_admin_mutator(
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    _: TenantCtx,
) -> User:
    ctx = require_tenant_context()
    roles: list[str] | None = None
    if ctx.tenant_id:
        result = await db.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == ctx.tenant_id,
                TenantMembership.user_id == user.id,
            )
        )
        membership = result.scalar_one_or_none()
        if membership:
            from app.core.admin_permissions import normalize_roles

            roles = normalize_roles(
                list(getattr(membership, "roles", None) or []),
                fallback=membership.role,
            )
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
    """Factory de dependencia FastAPI para permisos por acción, módulo y (futuro) empresa.

    - 401: sin usuario autenticado (via ``get_current_user``).
    - 403: usuario autenticado sin permiso suficiente.
    """

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


# Alias tipados para PR-1.3b (opt-in por router; no aplicados globalmente)
RequireViewDgcp = Annotated[PermissionContext, Depends(RequirePermission("view_dgcp"))]
RequireViewOdoo = Annotated[PermissionContext, Depends(RequirePermission("view_odoo"))]
RequireViewM365 = Annotated[PermissionContext, Depends(RequirePermission("view_m365"))]
RequireViewPrices = Annotated[PermissionContext, Depends(RequirePermission(module="prices"))]
RequireViewSuppliers = Annotated[PermissionContext, Depends(RequirePermission(module="suppliers"))]
