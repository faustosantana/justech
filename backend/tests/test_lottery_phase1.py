"""Pruebas Fase 1 — módulo Resultados de Loterías / Lotería IA."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String

from app.config import get_settings
from app.core.admin_permissions import (
    LOTTERY_CLIENT_PERMISSIONS,
    ROLE_PERMISSIONS,
    permissions_for_role,
    role_has_permission,
)
from app.core.lottery_isolation import path_allowed_for_lottery_client
from app.main import app
from app.models.lottery import (
    LotteryChatSession,
    LotteryDraw,
    LotteryDrawNumber,
    LotteryLottery,
    LotterySavedQuery,
)
from app.services.lottery_ai_contracts import LOTTERY_SYSTEM_PROMPT_SKELETON, LOTTERY_TOOL_CATALOG
from app.services.lottery_aliases import (
    describe_alias_resolution,
    is_ambiguous_nacional_dia,
    resolve_confirmed_source_id,
)


def test_lottery_models_import():
    assert LotteryLottery.__tablename__ == "lottery_lotteries"
    assert LotteryDraw.__tablename__ == "lottery_draws"
    assert LotteryDrawNumber.__tablename__ == "lottery_draw_numbers"


def test_number_columns_are_text():
    value_col = LotteryDrawNumber.__table__.c.number_value
    raw_col = LotteryDrawNumber.__table__.c.number_raw
    assert isinstance(value_col.type, String)
    assert isinstance(raw_col.type, String)
    assert value_col.type.length == 32


def test_draws_unique_supports_multiple_per_day():
    # Unicidad NULL-safe vive en índices de migración 028 (no UniqueConstraint ORM).
    idx_names = {ix.name for ix in LotteryDraw.__table__.indexes}
    # ORM indexes for query performance still present
    assert any("lottery_date" in (n or "") for n in idx_names)
    # number columns remain text
    assert LotteryDrawNumber.__table__.c.number_value.type.length == 32
    # Confirm migration 028 defines the real uniqueness
    mig = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "028_lottery_draw_uniqueness.py"
    text = mig.read_text(encoding="utf-8")
    assert "uq_lottery_draws_lottery_source_ref" in text
    assert "COALESCE(draw_time" in text


def test_tenant_isolation_on_user_tables():
    assert "tenant_id" in LotteryChatSession.__table__.c
    assert "user_id" in LotteryChatSession.__table__.c
    assert "tenant_id" in LotterySavedQuery.__table__.c
    assert "user_id" in LotterySavedQuery.__table__.c
    assert "tenant_id" not in LotteryLottery.__table__.c
    assert "tenant_id" not in LotteryDraw.__table__.c


def test_lottery_permissions_and_client_role():
    assert role_has_permission("lottery_client", "lottery.access")
    assert role_has_permission("lottery_client", "lottery.chat")
    assert not role_has_permission("lottery_client", "lottery.admin")
    assert not role_has_permission("lottery_client", "lottery.import")
    assert not role_has_permission("lottery_client", "view_odoo")
    assert not role_has_permission("usuario", "lottery.access")
    assert role_has_permission("owner", "lottery.admin")
    assert set(permissions_for_role("lottery_client")) == set(LOTTERY_CLIENT_PERMISSIONS)
    assert "lottery_client" in ROLE_PERMISSIONS


def test_nacional_dia_remains_ambiguous():
    assert is_ambiguous_nacional_dia("Nacional Día")
    assert is_ambiguous_nacional_dia("nacional dia")
    assert resolve_confirmed_source_id("Nacional Día") is None
    result = describe_alias_resolution("Nacional Día")
    assert result["resolved"] is False
    assert result["ambiguous"] is True
    assert len(result["candidates"]) == 2
    ids = {c["source_id"] for c in result["candidates"]}
    assert ids == {20, 21}


def test_confirmed_priority_aliases():
    assert resolve_confirmed_source_id("Real") == 13
    assert resolve_confirmed_source_id("Loteka") == 6
    assert resolve_confirmed_source_id("Leidsa") == 5
    assert resolve_confirmed_source_id("Nacional Noche") == 4
    assert resolve_confirmed_source_id("New York Día") == 16
    assert resolve_confirmed_source_id("New York Noche") == 17


def test_ai_contracts_have_no_free_sql():
    assert "SQL libre" in LOTTERY_SYSTEM_PROMPT_SKELETON or "sql libre" in LOTTERY_SYSTEM_PROMPT_SKELETON.lower()
    # Fase 4: tools tipadas implementadas (sin SQL libre)
    assert all(t.implemented for t in LOTTERY_TOOL_CATALOG)
    src = Path(__file__).resolve().parents[1] / "app" / "services" / "lottery_ai_contracts.py"
    text = src.read_text(encoding="utf-8")
    assert "execute(" not in text
    assert "text(\"SELECT" not in text.upper().replace(" ", "")


def test_lottery_client_api_allowlist():
    assert path_allowed_for_lottery_client("/api/v1/lottery/health")
    assert path_allowed_for_lottery_client("/api/v1/auth/login")
    assert path_allowed_for_lottery_client("/api/v1/health")
    assert not path_allowed_for_lottery_client("/api/v1/odoo/health")
    assert not path_allowed_for_lottery_client("/api/v1/m365/health")
    assert not path_allowed_for_lottery_client("/api/v1/admin/users")


def test_migration_file_exists_and_is_reversible():
    mig = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "027_lottery_module.py"
    assert mig.exists()
    text = mig.read_text(encoding="utf-8")
    assert 'revision: str = "027_lottery_module"' in text
    assert 'down_revision: Union[str, None] = "026_m365_imap_accounts"' in text
    assert "def upgrade()" in text
    assert "def downgrade()" in text
    assert "lottery_lotteries" in text
    assert "number_value" in text
    assert "uq_lottery_draws_natural_key" in text


def test_feature_flag_default_false(monkeypatch):
    monkeypatch.delenv("LOTTERY_MODULE_ENABLED", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.lottery_module_enabled is False
    assert settings.lottery_sync_enabled is False
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lottery_health_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/lottery/health")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_lottery_lotteries_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/lottery/lotteries")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_lottery_health_forbidden_without_permission():
    from app.api import deps
    from app.core.security import create_access_token
    import uuid

    token = create_access_token(
        subject=str(uuid.uuid4()),
        tenant_id=uuid.uuid4(),
        role="usuario",
    )

    fake_user = MagicMock()
    fake_user.is_superadmin = False
    fake_user.id = uuid.uuid4()
    fake_user.is_active = True

    async def _user():
        return fake_user

    async def _tenant():
        return None

    app.dependency_overrides[deps.get_current_user] = _user
    app.dependency_overrides[deps.resolve_tenant_context] = _tenant
    try:
        with patch("app.api.v1.lottery.get_current_role", return_value="usuario"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/lottery/health",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_feature_flag_blocks_lotteries_list():
    from app.api import deps
    from app.core.security import create_access_token
    import uuid

    token = create_access_token(
        subject=str(uuid.uuid4()),
        tenant_id=uuid.uuid4(),
        role="owner",
    )

    fake_user = MagicMock()
    fake_user.is_superadmin = False
    fake_user.id = uuid.uuid4()
    fake_user.is_active = True

    async def _user():
        return fake_user

    async def _tenant():
        return None

    app.dependency_overrides[deps.get_current_user] = _user
    app.dependency_overrides[deps.resolve_tenant_context] = _tenant
    try:
        with (
            patch("app.api.v1.lottery.get_current_role", return_value="owner"),
            patch("app.api.v1.lottery.settings") as mock_settings,
        ):
            mock_settings.lottery_module_enabled = False
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/lottery/lotteries",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_lottery_client_isolation_middleware_blocks_odoo():
    from app.core.security import create_access_token
    import uuid

    token = create_access_token(
        subject=str(uuid.uuid4()),
        tenant_id=uuid.uuid4(),
        role="lottery_client",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/odoo/health",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
    assert "Lottery Client" in response.json().get("detail", "")


def test_assistant_source_lottery_exists():
    from app.assistant.router import AssistantSource

    assert AssistantSource.LOTTERY.value == "lottery"


def test_default_modules_includes_lottery_disabled_seed():
    from app.core.admin_permissions import DEFAULT_MODULES

    lottery = [m for m in DEFAULT_MODULES if m[0] == "lottery"]
    assert lottery
    assert lottery[0][2] is True  # is_future → seeded disabled
