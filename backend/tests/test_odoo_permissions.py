"""Tests permisos y configuración Odoo."""

import pytest

from app.services.odoo_config_service import OdooConfigService
from app.services.odoo_permission_service import MODULE_MODELS, OdooPermissionService


@pytest.mark.asyncio
async def test_config_status_missing_credentials():
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from app.models.tenant import Tenant

        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one_or_none()
        if not tenant:
            pytest.skip("Sin tenant en entorno de test")
        status = await OdooConfigService(db, tenant.id).status()
    assert "configured" in status
    assert "missing" in status
    assert "message" in status


def test_derive_modules_from_model_access():
    model_access = {
        "sale.order": {"read": True, "write": False, "create": True, "unlink": False},
        "account.move": {"read": False, "write": False, "create": False, "unlink": False},
        "res.partner": {"read": True, "write": True, "create": True, "unlink": False},
        "project.task": {"read": True, "write": False, "create": False, "unlink": False},
    }
    modules = OdooPermissionService._derive_modules(model_access)
    assert modules["sales"]["enabled"] is True
    assert modules["sales"]["create"] is True
    assert modules["accounting"]["enabled"] is False
    assert modules["contacts"]["create"] is True
    assert modules["project"]["enabled"] is True
    assert modules["project"]["create"] is False


def test_module_models_cover_core_areas():
    assert "sales" in MODULE_MODELS
    assert "accounting" in MODULE_MODELS
    assert "sale.order" in MODULE_MODELS["sales"]
