"""Tests — multirol, unión de permisos y anti-escalación."""

from __future__ import annotations

from app.core.admin_permissions import (
    actor_can_assign_roles,
    can_mutate_admin,
    can_view_admin,
    normalize_roles,
    permissions_for_roles,
    primary_role,
    roles_have_permission,
)


def test_normalize_roles_dedup_and_fallback():
    assert normalize_roles(["usuario", "usuario", "licitaciones"]) == ["usuario", "licitaciones"]
    assert normalize_roles([], fallback="owner") == ["owner"]
    assert normalize_roles(["member"]) == ["usuario"]


def test_primary_role_prefers_owner():
    assert primary_role(["licitaciones", "owner", "usuario"]) == "owner"
    assert primary_role(["usuario", "licitaciones"]) == "licitaciones"


def test_role_union_permissions():
    perms = permissions_for_roles(["usuario", "licitaciones"])
    assert "view_dgcp" in perms
    assert "mutate_dgcp" in perms
    assert "view_modules" in perms
    # lottery_client alone must not gain documents
    assert "view_documents" not in permissions_for_roles(["lottery_client"])
    assert roles_have_permission(["licitaciones", "finanzas"], "view_dgcp")
    assert roles_have_permission(["finanzas"], "view_odoo")


def test_admin_gates_with_multirol():
    assert can_view_admin(None, roles=["gerencia", "usuario"])
    assert can_mutate_admin(None, roles=["admin", "licitaciones"])
    assert not can_mutate_admin(None, roles=["licitaciones", "usuario"])


def test_no_autoescalation_to_owner():
    ok, err = actor_can_assign_roles(
        actor_roles=["admin"],
        actor_is_superadmin=False,
        requested_roles=["owner", "usuario"],
    )
    assert not ok
    assert err and "Propietario" in err

    ok2, _ = actor_can_assign_roles(
        actor_roles=["owner"],
        actor_is_superadmin=False,
        requested_roles=["owner", "licitaciones"],
    )
    assert ok2


def test_mutate_dgcp_present_for_licitaciones():
    assert roles_have_permission(["licitaciones"], "mutate_dgcp")
    assert roles_have_permission(["usuario"], "mutate_dgcp")
