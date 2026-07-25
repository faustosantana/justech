"""Fase 6 — shares seguros, sync dry-run, environment guards."""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings, settings
from app.core.admin_permissions import role_has_permission
from app.models.lottery import LotteryDraw, LotteryLottery
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.lottery_share import LotteryShareCreateRequest
from app.services.lottery_importer import assert_not_production_database
from fastapi import HTTPException
from app.services.lottery_share_service import LotteryShareService, view_shared_by_token
from app.services.lottery_sync_service import (
    LotterySyncService,
    SyncEnvironmentGuardError,
    assert_sync_environment_safe,
)

DEV_URL = "postgresql+asyncpg://jaios:jaios_dev_local_only@localhost:5433/jaios_lottery_dev"
# Snapshot opcional vía env — sin path de laptop hardcodeado (Pre-J11A TD-001).
SQLITE = Path(os.environ["LOTTERY_SYNC_SQLITE_PATH"]) if os.environ.get("LOTTERY_SYNC_SQLITE_PATH") else None


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("LOTTERY_MODULE_ENABLED", "true")
    monkeypatch.setenv("LOTTERY_SYNC_ENABLED", "false")
    monkeypatch.setenv("LOTTERY_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("LOTTERY_SCRAPING_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", DEV_URL)
    get_settings.cache_clear()
    from app import config

    config.get_settings.cache_clear()
    monkeypatch.setattr(settings, "lottery_module_enabled", True)
    monkeypatch.setattr(settings, "lottery_sync_enabled", False)
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", False)
    monkeypatch.setattr(settings, "lottery_scraping_enabled", False)
    yield
    get_settings.cache_clear()


@pytest.fixture
async def db_session():
    eng = create_async_engine(DEV_URL)
    Session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            yield session
            await session.rollback()
    except Exception as exc:
        pytest.skip(f"dev db: {exc}")
    finally:
        await eng.dispose()


async def _seed(db: AsyncSession):
    suffix = uuid.uuid4().hex[:8]
    tenant = Tenant(slug=f"p6-{suffix}", name=f"P6 {suffix}", settings={}, metadata_={})
    user = User(
        email=f"p6-{suffix}@example.com",
        password_hash="x",
        full_name="P6",
        is_active=True,
        is_superadmin=True,
    )
    db.add_all([tenant, user])
    await db.flush()
    return tenant.id, user.id


def test_lottery_share_permission_not_on_client():
    assert role_has_permission("admin", "lottery.share")
    assert role_has_permission("owner", "lottery.share")
    assert not role_has_permission("lottery_client", "lottery.share")


def test_staging_allowlist_and_prod_guard():
    assert_not_production_database(
        "postgresql+asyncpg://jaios_staging:x@localhost:5434/jaios_lottery_staging"
    )
    with pytest.raises(Exception):
        assert_not_production_database(
            "postgresql+asyncpg://u:p@jaios.justech.do:5432/jaios"
        )


def test_sync_env_guard_blocks_write_on_dev(monkeypatch):
    """Fase 8: scheduler puede estar activo; escritura solo staging:5434."""
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", True)
    assert_sync_environment_safe(DEV_URL, allow_write=False)  # dry-run OK
    with pytest.raises(SyncEnvironmentGuardError):
        assert_sync_environment_safe(DEV_URL, allow_write=True)


@pytest.mark.asyncio
async def test_share_create_view_revoke_expire(db_session):
    # Ensure migration 030 applied on lottery_dev
    from sqlalchemy import text

    try:
        await db_session.execute(text("SELECT 1 FROM jaios.lottery_shared_queries LIMIT 1"))
    except Exception:
        pytest.skip("migration 030 not applied on lottery_dev")

    tenant_id, user_id = await _seed(db_session)
    svc = LotteryShareService(db_session, tenant_id=tenant_id, user_id=user_id)
    created = await svc.create(
        LotteryShareCreateRequest(
            query_type="by_date",
            query_parameters={"lottery": "Real", "date": "2022-03-15"},
            title="Real 15-mar-2022",
            ttl_hours=1,
            max_views=2,
            allow_export=False,
        )
    )
    assert created.token
    assert created.share_url
    assert "tenant" not in (created.token or "")

    view = await view_shared_by_token(db_session, created.token)
    assert view.title == "Real 15-mar-2022"
    assert "01" in str(view.result)
    assert "tenant_id" not in str(view.result).lower()
    assert view.disclaimer

    await view_shared_by_token(db_session, created.token)
    with pytest.raises(HTTPException):
        await view_shared_by_token(db_session, created.token)

    # new share for revoke
    created2 = await svc.create(
        LotteryShareCreateRequest(
            query_type="by_date",
            query_parameters={"lottery": "Real", "date": "2022-03-15"},
            title="Revocar",
            ttl_hours=1,
            max_views=10,
        )
    )
    await svc.revoke(created2.share_id)
    with pytest.raises(HTTPException):
        await view_shared_by_token(db_session, created2.token or "")

    # invalid token
    with pytest.raises(HTTPException):
        await view_shared_by_token(db_session, "x" * 40)

    # tenant isolation: other user cannot get owned share
    t2, u2 = await _seed(db_session)
    other = LotteryShareService(db_session, tenant_id=t2, user_id=u2)
    with pytest.raises(HTTPException):
        await other.get_mine(created.share_id)


@pytest.mark.asyncio
async def test_sync_dry_run_no_write(db_session):
    if SQLITE is None or not SQLITE.exists():
        pytest.skip("sqlite source missing (set LOTTERY_SYNC_SQLITE_PATH)")
    before = int(await db_session.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    assert before == 91927
    svc = LotterySyncService(db_session, database_url=DEV_URL)
    report = await svc.dry_run(
        source="sqlite",
        sqlite_path=SQLITE,
        from_date=date(2022, 3, 1),
        to_date=date(2022, 3, 31),
        lottery_source_id=13,
        limit=100,
    )
    after = int(await db_session.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    assert after == before == 91927
    assert report.wrote_to_database is False
    assert report.dry_run is True
    assert report.records_fetched >= 1
    assert report.status in ("completed", "failed")
    # zeros preserved in sample numbers when present
    for item in report.sample:
        for n in item.get("numbers") or []:
            assert isinstance(n, str)


def test_no_prediction_language_in_share_schema():
    from app.schemas import lottery_share as m

    text = Path(m.__file__).read_text(encoding="utf-8").lower()
    for bad in ("predicción", "caliente", "apuesta segura", "próximo ganador"):
        assert bad not in text
