import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.admin_permissions import can_mutate_admin, can_view_admin
from app.core.exceptions import forbidden, unauthorized
from app.core.security import verify_access_token
from app.core.tenant import get_current_role, parse_tenant_header, require_tenant_context, set_tenant_context
from app.db.session import get_db
from app.models.tenant import TenantMembership
from app.models.user import User

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
    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    return result.scalar_one_or_none()


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


async def require_admin_viewer(
    user: Annotated[User, Depends(get_current_user)],
    _: TenantCtx,
) -> User:
    if not can_view_admin(get_current_role(), user.is_superadmin):
        raise forbidden("Acceso restringido al Centro de Administración")
    return user


async def require_admin_mutator(
    user: Annotated[User, Depends(get_current_user)],
    _: TenantCtx,
) -> User:
    if not can_mutate_admin(get_current_role(), user.is_superadmin):
        raise forbidden("Permisos insuficientes para modificar administración")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminViewer = Annotated[User, Depends(require_admin_viewer)]
AdminMutator = Annotated[User, Depends(require_admin_mutator)]
