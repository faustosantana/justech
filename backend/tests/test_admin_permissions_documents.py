"""Regression: view_documents for empresas-grupo module access (minimum restore)."""

from __future__ import annotations

from app.core.admin_permissions import (
    LOTTERY_CLIENT_PERMISSIONS,
    LOTTERY_PERMISSIONS,
    PERMISSIONS,
    ROLE_PERMISSIONS,
    permissions_for_role,
    role_has_permission,
)


def _perms(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS[role])


def test_canonical_name_view_documents_in_permissions():
    assert "view_documents" in PERMISSIONS
    # No obsolete aliases introduced by this hotfix
    for obsolete in ("view_docs", "documents.view", "view_document", "docs.view"):
        assert obsolete not in PERMISSIONS


def test_view_assistant_not_part_of_this_hotfix():
    assert "view_assistant" not in PERMISSIONS
    for role, perms in ROLE_PERMISSIONS.items():
        assert "view_assistant" not in perms, role


def test_platform_access_permissions_for_role_matrix():
    """GET /users/me/platform-access uses permissions_for_role(role)."""
    for role in ("owner", "admin"):
        assert "view_documents" in permissions_for_role(role)
    for role in ("gerencia", "usuario", "member"):
        assert "view_documents" in permissions_for_role(role)
    assert "view_documents" not in permissions_for_role("lottery_client")


def test_owner_admin_gerencia_usuario_have_view_documents():
    for role in ("owner", "admin", "gerencia", "usuario", "member"):
        assert role_has_permission(role, "view_documents"), role
        assert "view_documents" in _perms(role)


def test_historical_roles_with_documents_restored():
    for role in (
        "ventas",
        "facturacion",
        "finanzas",
        "compras",
        "soporte",
        "operaciones",
        "licitaciones",
    ):
        assert role_has_permission(role, "view_documents"), role


def test_lottery_client_denied_documents_keeps_lottery_set():
    assert not role_has_permission("lottery_client", "view_documents")
    assert "view_documents" not in ROLE_PERMISSIONS["lottery_client"]
    assert ROLE_PERMISSIONS["lottery_client"] == LOTTERY_CLIENT_PERMISSIONS
    for perm in ("lottery.access", "lottery_view", "lottery.chat"):
        assert role_has_permission("lottery_client", perm)


def test_owner_admin_lottery_permissions_unchanged():
    for role in ("owner", "admin"):
        for perm in ("lottery.admin", "lottery_admin_ai", "lottery.access", "lottery_view"):
            assert role_has_permission(role, perm), (role, perm)


def test_non_documents_module_permissions_unchanged_for_usuario():
    """Restore does not grant unrelated module keys to usuario."""
    u = _perms("usuario")
    assert "view_odoo" in u and "view_dgcp" in u and "view_m365" in u
    assert "admin_users" not in u
    assert "admin_settings" not in u
    assert not (u & (LOTTERY_PERMISSIONS - LOTTERY_CLIENT_PERMISSIONS))


def test_module_guard_logic_empresas_grupo_requires_view_documents():
    """Mirrors frontend canViewAppByRole for empresas-grupo (strict view_documents)."""

    def can_access_empresas(permissions: list[str]) -> bool:
        return "view_documents" in permissions

    assert can_access_empresas(["view_documents", "view_modules"]) is True
    assert can_access_empresas(["view_modules"]) is False
    assert can_access_empresas(["view_odoo"]) is False
    assert can_access_empresas([]) is False
