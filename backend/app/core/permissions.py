"""Resolución y evaluación de permisos — compatible con admin_permissions y module_access."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_permissions import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
    normalize_role,
    normalize_roles,
    permissions_for_roles,
    primary_role,
)
from app.core.module_access import MODULE_PRICES, MODULE_SUPPLIERS, get_membership, user_has_module
from app.core.tenant import require_tenant_context
from app.models.tenant import TenantMembership
from app.models.user import User

PermissionAction = Literal["view", "mutate", "manage"]

# Alias frontend app id → module_access key
MODULE_KEY_ALIASES: dict[str, str] = {
    "precios": MODULE_PRICES,
    "prices": MODULE_PRICES,
    "proveedores": MODULE_SUPPLIERS,
    "suppliers": MODULE_SUPPLIERS,
}

# Módulos lógicos → permiso de acción (ROLE_PERMISSIONS)
MODULE_ACTION_PERMISSION: dict[str, str] = {
    "dgcp": "view_dgcp",
    "licitaciones": "view_dgcp",
    "odoo": "view_odoo",
    "m365": "view_m365",
    "documents": "view_documents",
    "documentos": "view_documents",
    "prices": "view_prices",
    "precios": "view_prices",
    "suppliers": "view_supplier_integrations",
    "proveedores": "view_supplier_integrations",
    "hermes": "view_assistant",
    "assistant": "view_assistant",
    "tasks": "view_modules",
}

ACTION_EXTRA_PERMISSION: dict[str, str] = {
    "manage": "manage_supplier_integrations",
}


class PermissionDeniedReason(str, Enum):
    MISSING_ACTION = "missing_action"
    MISSING_MODULE = "missing_module"
    MODULE_DISABLED = "module_disabled"
    COMPANY_SCOPE = "company_scope"


@dataclass(frozen=True)
class PermissionContext:
    """Contexto resuelto para evaluar permisos en un request autenticado."""

    user: User
    tenant_id: uuid.UUID
    role: str
    roles: tuple[str, ...]
    permissions: frozenset[str]
    membership: TenantMembership | None
    is_superadmin: bool


def membership_roles(membership: TenantMembership | None) -> list[str]:
    if not membership:
        return ["usuario"]
    stored = getattr(membership, "roles", None) or []
    return normalize_roles(list(stored) if stored else None, fallback=membership.role)


def effective_permissions(role: str | None, *, is_superadmin: bool = False, roles: list[str] | None = None) -> frozenset[str]:
    if is_superadmin:
        return PERMISSIONS
    if roles is not None:
        return permissions_for_roles(roles, is_superadmin=False)
    return ROLE_PERMISSIONS.get(normalize_role(role), ROLE_PERMISSIONS["usuario"])


def resolve_effective_role(
    *,
    jwt_role: str | None,
    membership_role: str | None,
    membership_roles_list: list[str] | None = None,
) -> str:
    if membership_roles_list:
        return primary_role(membership_roles_list, fallback=membership_role or jwt_role)
    if membership_role:
        return normalize_role(membership_role)
    return normalize_role(jwt_role)


def has_action_permission(
    ctx: PermissionContext,
    permission: str,
) -> bool:
    if ctx.is_superadmin:
        return True
    return permission in ctx.permissions


def has_any_action_permission(ctx: PermissionContext, *permissions: str) -> bool:
    return any(has_action_permission(ctx, p) for p in permissions)


def has_all_action_permissions(ctx: PermissionContext, *permissions: str) -> bool:
    return all(has_action_permission(ctx, p) for p in permissions)


def permission_for_module(module: str, action: PermissionAction = "view") -> str | None:
    key = MODULE_KEY_ALIASES.get(module, module)
    if action == "manage":
        return ACTION_EXTRA_PERMISSION.get("manage")
    return MODULE_ACTION_PERMISSION.get(key) or MODULE_ACTION_PERMISSION.get(module)


def normalize_module_key(module: str) -> str:
    return MODULE_KEY_ALIASES.get(module, module)


async def has_module_access(
    db: AsyncSession,
    ctx: PermissionContext,
    module: str,
    action: PermissionAction = "view",
) -> bool:
    module_key = normalize_module_key(module)

    # Módulos con gate en module_access (prices / suppliers live)
    if module_key in {MODULE_PRICES, MODULE_SUPPLIERS}:
        if not await user_has_module(
            db,
            ctx.tenant_id,
            ctx.user.id,
            ctx.role,
            module_key,
            membership=ctx.membership,
        ):
            return False

    perm = permission_for_module(module, action)
    if perm is None:
        return True
    return has_action_permission(ctx, perm)


def check_company_scope(
    ctx: PermissionContext,
    *,
    company_key: str | None = None,
    company_id: uuid.UUID | None = None,
) -> bool:
    """RBAC por empresa del grupo — reservado para fase Party / visible_company_ids."""
    _ = ctx, company_key, company_id
    return True


async def build_permission_context(db: AsyncSession, user: User) -> PermissionContext:
    tenant_ctx = require_tenant_context()
    membership = await get_membership(db, tenant_ctx.tenant_id, user.id)
    roles = membership_roles(membership)
    role = resolve_effective_role(
        jwt_role=tenant_ctx.role,
        membership_role=membership.role if membership else None,
        membership_roles_list=roles,
    )
    return PermissionContext(
        user=user,
        tenant_id=tenant_ctx.tenant_id,
        role=role,
        roles=tuple(roles),
        permissions=effective_permissions(role, is_superadmin=user.is_superadmin, roles=roles),
        membership=membership,
        is_superadmin=user.is_superadmin,
    )


def format_permission_denied_message(
    *,
    permissions: tuple[str, ...] = (),
    module: str | None = None,
    action: PermissionAction = "view",
    company_key: str | None = None,
    reason: PermissionDeniedReason = PermissionDeniedReason.MISSING_ACTION,
) -> str:
    parts: list[str] = []
    if permissions:
        parts.append(f"permiso(s): {', '.join(permissions)}")
    if module:
        parts.append(f"módulo: {module} (acción: {action})")
    if company_key:
        parts.append(f"empresa: {company_key}")
    detail = "; ".join(parts) if parts else "permiso requerido"
    if reason == PermissionDeniedReason.MODULE_DISABLED:
        return f"Módulo no habilitado o no asignado — {detail}"
    if reason == PermissionDeniedReason.COMPANY_SCOPE:
        return f"Sin acceso a la empresa indicada — {detail}"
    return f"Permiso insuficiente — {detail}"


async def evaluate_permission_requirement(
    db: AsyncSession,
    ctx: PermissionContext,
    *,
    permissions: tuple[str, ...] = (),
    module: str | None = None,
    action: PermissionAction = "view",
    require_all: bool = True,
    company_key: str | None = None,
) -> tuple[bool, PermissionDeniedReason, str]:
    if company_key and not check_company_scope(ctx, company_key=company_key):
        return (
            False,
            PermissionDeniedReason.COMPANY_SCOPE,
            format_permission_denied_message(
                permissions=permissions,
                module=module,
                action=action,
                company_key=company_key,
                reason=PermissionDeniedReason.COMPANY_SCOPE,
            ),
        )

    if permissions:
        ok = (
            has_all_action_permissions(ctx, *permissions)
            if require_all
            else has_any_action_permission(ctx, *permissions)
        )
        if not ok:
            return (
                False,
                PermissionDeniedReason.MISSING_ACTION,
                format_permission_denied_message(
                    permissions=permissions,
                    module=module,
                    action=action,
                    company_key=company_key,
                ),
            )

    if module:
        if not await has_module_access(db, ctx, module, action):
            module_key = normalize_module_key(module)
            reason = (
                PermissionDeniedReason.MODULE_DISABLED
                if module_key in {MODULE_PRICES, MODULE_SUPPLIERS}
                else PermissionDeniedReason.MISSING_MODULE
            )
            return (
                False,
                reason,
                format_permission_denied_message(
                    permissions=permissions,
                    module=module,
                    action=action,
                    company_key=company_key,
                    reason=reason,
                ),
            )

    return True, PermissionDeniedReason.MISSING_ACTION, ""
