"""Acceso a módulos de plataforma por rol + asignación por usuario."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_permissions import (
    can_mutate_admin,
    can_view_admin,
    normalize_role,
    normalize_roles,
    permissions_for_role,
    permissions_for_roles,
    primary_role,
)
from app.models.tenant import TenantMembership
from app.models.tenant_module import TenantModule

MODULE_PRICES = "prices"
MODULE_SUPPLIERS = "suppliers"

ASSIGNABLE_MODULES: list[tuple[str, str]] = [
    (MODULE_PRICES, "Inteligencia de precios"),
    (MODULE_SUPPLIERS, "Proveedores live (Ingram / Omega)"),
]

SUPPLIER_INTEGRATION_PROVIDERS = frozenset({
    "ingram", "omega", "intcomex", "tecnomarket", "cecomsa", "tecnosinergia",
})

# Por defecto todos los roles ven precios y proveedores live.
ROLE_MODULE_DEFAULTS: dict[str, frozenset[str]] = {
    role: frozenset({MODULE_PRICES, MODULE_SUPPLIERS})
    for role in (
        "owner",
        "admin",
        "gerencia",
        "ventas",
        "facturacion",
        "finanzas",
        "compras",
        "soporte",
        "operaciones",
        "licitaciones",
        "usuario",
        "member",
    )
}


async def get_membership(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TenantMembership | None:
    result = await db.execute(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


def modules_for_membership(role: str | None, allowed_modules: list | None) -> set[str]:
    if allowed_modules is not None:
        return {str(m) for m in allowed_modules}
    return set(ROLE_MODULE_DEFAULTS.get(normalize_role(role), {MODULE_PRICES, MODULE_SUPPLIERS}))


async def tenant_module_enabled(db: AsyncSession, tenant_id: uuid.UUID, module_key: str) -> bool:
    result = await db.execute(
        select(TenantModule.is_enabled).where(
            TenantModule.tenant_id == tenant_id,
            TenantModule.module_key == module_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        # Sin fila: habilitado salvo keys explícitamente "future" en seed histórico.
        return True
    return bool(row)


async def user_has_module(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str | None,
    module_key: str,
    *,
    membership: TenantMembership | None = None,
) -> bool:
    if not await tenant_module_enabled(db, tenant_id, module_key):
        return False
    mem = membership or await get_membership(db, tenant_id, user_id)
    allowed = mem.allowed_modules if mem else None
    effective_role = mem.role if mem else role
    return module_key in modules_for_membership(effective_role, allowed)


async def platform_access(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str | None,
    *,
    is_superadmin: bool = False,
) -> dict:
    mem = await get_membership(db, tenant_id, user_id)
    roles = normalize_roles(
        list(getattr(mem, "roles", None) or []) if mem else None,
        fallback=(mem.role if mem else role),
    )
    effective_role = primary_role(roles) if mem else normalize_role(role)
    allowed = getattr(mem, "allowed_modules", None) if mem else None
    user_modules = modules_for_membership(effective_role, allowed)

    prices_enabled = await tenant_module_enabled(db, tenant_id, MODULE_PRICES)
    suppliers_enabled = await tenant_module_enabled(db, tenant_id, MODULE_SUPPLIERS)

    perms = set(permissions_for_roles(roles, is_superadmin=is_superadmin))
    if is_superadmin:
        perms.add("manage_supplier_integrations")

    can_view_prices = prices_enabled and MODULE_PRICES in user_modules
    can_view_suppliers = suppliers_enabled and MODULE_SUPPLIERS in user_modules
    can_manage_supplier_integrations = (
        is_superadmin
        or "manage_supplier_integrations" in perms
        or any(r in {"owner", "admin", "gerencia", "compras"} for r in roles)
    )

    return {
        "role": effective_role,
        "permissions": sorted(perms),
        "allowed_modules": allowed,
        "modules": {
            MODULE_PRICES: can_view_prices,
            MODULE_SUPPLIERS: can_view_suppliers,
        },
        "can_view_prices": can_view_prices,
        "can_view_suppliers": can_view_suppliers,
        "can_manage_supplier_integrations": can_manage_supplier_integrations and can_view_suppliers,
        "can_mutate_admin": can_mutate_admin(effective_role, is_superadmin, roles=roles),
        "can_view_admin": can_view_admin(effective_role, is_superadmin, roles=roles),
    }
