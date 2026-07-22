"""Pruebas Fase 5 — producto, favoritos, exports, aislamiento."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings, settings
from app.main import app
from app.models.lottery import LotteryLottery
from app.models.tenant import Tenant
from app.models.user import User
from app.services.lottery_export_service import LotteryExportService, _safe_cell
from app.services.lottery_product_service import LotteryProductService
from app.schemas.lottery_product import LotteryExportRequest, LotteryPreferencesUpdate
from sqlalchemy import select

DEV_URL = "postgresql+asyncpg://jaios:jaios_dev_local_only@localhost:5433/jaios_lottery_dev"


@pytest.fixture(autouse=True)
def _enable(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("LOTTERY_MODULE_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", DEV_URL)
    monkeypatch.setenv("LOTTERY_EXPORTS_PATH", str(tmp_path / "exports"))
    get_settings.cache_clear()
    from app.api.v1 import lottery as lottery_api
    from app import config

    config.get_settings.cache_clear()
    monkeypatch.setattr(lottery_api.settings, "lottery_module_enabled", True)
    monkeypatch.setattr(settings, "lottery_exports_path", str(tmp_path / "exports"))
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
    tenant = Tenant(slug=f"p5-{suffix}", name=f"P5 {suffix}", settings={}, metadata_={})
    user = User(
        email=f"p5-{suffix}@example.com",
        password_hash="x",
        full_name="P5",
        is_active=True,
        is_superadmin=True,
    )
    db.add_all([tenant, user])
    await db.flush()
    return tenant.id, user.id


@pytest.mark.asyncio
async def test_dashboard_favorites_prefs_export(db_session):
    tenant_id, user_id = await _seed(db_session)
    prod = LotteryProductService(db_session, tenant_id=tenant_id, user_id=user_id)
    dash = await prod.dashboard()
    assert dash.lotteries_count >= 50
    assert dash.draws_count == 91927
    assert dash.sync_enabled is False

    lot = (
        await db_session.execute(select(LotteryLottery).where(LotteryLottery.source_id == 13))
    ).scalar_one()
    fav = await prod.add_favorite(lot.id)
    assert fav.lottery.source_id == 13
    listed = await prod.list_favorites()
    assert listed.total == 1

    detail = await prod.get_lottery_by_slug(lot.slug)
    assert detail.lottery.name == "Quiniela Real"
    assert detail.is_favorite is True

    prefs = await prod.update_preferences(
        LotteryPreferencesUpdate(onboarding_completed=True, preferred_export_format="csv")
    )
    assert prefs.onboarding_completed is True

    await prod.record_recent(query_type="by_date", title="Real 2022-03-15", parameters={"date": "2022-03-15"})
    recent = await prod.list_recent()
    assert recent.total >= 1

    # other tenant isolation
    t2, u2 = await _seed(db_session)
    other = LotteryProductService(db_session, tenant_id=t2, user_id=u2)
    assert (await other.list_favorites()).total == 0

    exp = LotteryExportService(db_session, tenant_id=tenant_id, user_id=user_id)
    created = await exp.create(
        LotteryExportRequest(
            query_type="by_date",
            query_parameters={"lottery": "Real", "date": "2022-03-15"},
            format="csv",
            title="real-2022-03-15",
        )
    )
    assert created.filename.endswith(".csv")
    row, content = await exp.download(created.export_id)
    text = content.decode("utf-8-sig")
    assert "01" in text
    assert "19" in text
    assert "07" in text
    # formula injection mitigation
    assert _safe_cell("=1+1").startswith("'")

    xlsx = await exp.create(
        LotteryExportRequest(
            query_type="by_date",
            query_parameters={"lottery": "Real", "date": "2022-03-15"},
            format="xlsx",
        )
    )
    _, xb = await exp.download(xlsx.export_id)
    assert xb[:2] == b"PK"

    pdf = await exp.create(
        LotteryExportRequest(
            query_type="by_date",
            query_parameters={"lottery": "Real", "date": "2022-03-15"},
            format="pdf",
        )
    )
    _, pb = await exp.download(pdf.export_id)
    assert pb[:4] == b"%PDF"
    assert len(pb) > 500

    await db_session.commit()


def test_csv_injection_helper():
    assert _safe_cell("05") == "05"
    assert _safe_cell("00") == "00"
    assert _safe_cell("+cmd") .startswith("'")
    assert _safe_cell("@x").startswith("'")


def test_path_traversal_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "lottery_exports_path", str(tmp_path))
    from app.services.lottery_export_service import _safe_storage_path
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _safe_storage_path("../etc/passwd")
    with pytest.raises(HTTPException):
        _safe_storage_path("a/b.csv")


@pytest.mark.asyncio
async def test_export_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/lottery/exports", json={})
        assert r.status_code == 401


def test_migration_029_exists():
    mig = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "029_lottery_productization.py"
    assert mig.exists()
    text = mig.read_text()
    assert "lottery_user_favorites" in text
    assert "028_lottery_draw_uniqueness" in text


def test_share_links_secure_endpoints_exist():
    """Fase 6: shares seguros con token hash + snapshot (no acceso JAIOS general)."""
    from pathlib import Path

    api = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "lottery.py"
    text = api.read_text()
    assert '/shares"' in text or "/shares'" in text or '"/shares"' in text or "@router.post(\"/shares\"" in text
    assert "/shared/{token}" in text
    assert "lottery.share" in text
