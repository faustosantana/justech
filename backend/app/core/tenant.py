import uuid
from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

TENANT_HEADER = "X-Tenant-ID"

_current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("tenant_id", default=None)
_current_user_id: ContextVar[uuid.UUID | None] = ContextVar("user_id", default=None)
_current_role: ContextVar[str | None] = ContextVar("role", default=None)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None
    role: str | None = None


def set_tenant_context(
    *,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None = None,
    role: str | None = None,
) -> None:
    _current_tenant_id.set(tenant_id)
    _current_user_id.set(user_id)
    _current_role.set(role)


def get_current_tenant_id() -> uuid.UUID | None:
    return _current_tenant_id.get()


def get_current_user_id() -> uuid.UUID | None:
    return _current_user_id.get()


def get_current_role() -> str | None:
    return _current_role.get()


def require_tenant_context() -> TenantContext:
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required. Provide X-Tenant-ID header.",
        )
    return TenantContext(
        tenant_id=tenant_id,
        user_id=get_current_user_id(),
        role=get_current_role(),
    )


def parse_tenant_header(x_tenant_id: str | None = Header(default=None, alias=TENANT_HEADER)) -> uuid.UUID | None:
    if not x_tenant_id:
        return None
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID format.",
        ) from exc
