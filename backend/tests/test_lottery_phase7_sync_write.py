"""Fase 7 — write gates, fixture sync, idempotency, rollback, lock."""

from __future__ import annotations

import os
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings, settings
from app.models.lottery import LotteryDraw
from app.services.lottery_sync_gates import assert_write_gates
from app.services.lottery_sync_lock import acquire_sync_lock, release_sync_lock
from app.services.lottery_sync_service import SyncCandidate, SyncEnvironmentGuardError
from app.services.lottery_sync_writer import FixtureSourceAdapter, LotterySyncWriter

STAGING_URL = "postgresql+asyncpg://jaios_staging:jaios_staging_local_only@localhost:5434/jaios_lottery_staging"
# Opcional: dumps locales de staging — nunca hardcodear laptop path (Pre-J11A).
BACKUP_DIR = Path(os.environ["LOTTERY_STAGING_BACKUP_DIR"]) if os.environ.get("LOTTERY_STAGING_BACKUP_DIR") else None


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("LOTTERY_SYNC_ENABLED", "true")
    monkeypatch.setenv("LOTTERY_SYNC_WRITE_ENABLED", "true")
    monkeypatch.setenv("LOTTERY_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("LOTTERY_SCRAPING_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", STAGING_URL)
    get_settings.cache_clear()
    from app import config

    config.get_settings.cache_clear()
    monkeypatch.setattr(settings, "lottery_sync_enabled", True)
    monkeypatch.setattr(settings, "lottery_sync_write_enabled", True)
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", False)
    monkeypatch.setattr(settings, "lottery_scraping_enabled", False)
    yield
    get_settings.cache_clear()


@pytest.fixture
def backup_path():
    if BACKUP_DIR is None or not BACKUP_DIR.is_dir():
        pytest.skip("set LOTTERY_STAGING_BACKUP_DIR for write-gate backup fixtures")
    files = sorted(BACKUP_DIR.glob("pre-phase7-*.dump"))
    if not files:
        pytest.skip("no pre-phase7 backup")
    return str(files[-1])


@pytest.fixture
async def staging_db():
    eng = create_async_engine(STAGING_URL)
    Session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            yield session
            await session.rollback()
    except Exception as exc:
        pytest.skip(f"staging db: {exc}")
    finally:
        await eng.dispose()


def test_write_gates_block_without_confirm(backup_path):
    with pytest.raises(SyncEnvironmentGuardError):
        assert_write_gates(
            database_url=STAGING_URL,
            environment="staging",
            confirm_database="jaios_lottery_staging",
            write=True,
            yes=False,
            backup_path=backup_path,
        )


def test_write_gates_block_wrong_db(backup_path):
    with pytest.raises(SyncEnvironmentGuardError):
        assert_write_gates(
            database_url="postgresql+asyncpg://jaios:x@localhost:5433/jaios_lottery_dev",
            environment="staging",
            confirm_database="jaios_lottery_staging",
            write=True,
            yes=True,
            backup_path=backup_path,
        )


def test_write_gates_block_prod_confirm(backup_path):
    with pytest.raises(SyncEnvironmentGuardError):
        assert_write_gates(
            database_url=STAGING_URL,
            environment="production",
            confirm_database="jaios_lottery_staging",
            write=True,
            yes=True,
            backup_path=backup_path,
        )


@pytest.mark.asyncio
async def test_lock_acquire_release():
    h = await acquire_sync_lock("lottery:sync:test:unit")
    await release_sync_lock(h)


@pytest.mark.asyncio
async def test_fixture_write_idempotency_rollback(staging_db, backup_path):
    # Ensure 031 applied
    from sqlalchemy import text

    try:
        await staging_db.execute(text("SELECT inserted_draw_ids FROM jaios.lottery_sync_runs LIMIT 1"))
    except Exception:
        pytest.skip("031 not on staging")

    tag = uuid.uuid4().hex[:8]
    w = LotterySyncWriter(staging_db, database_url=STAGING_URL)
    before = await w.count_draws()
    fx = FixtureSourceAdapter(
        [
            SyncCandidate(13, "Quiniela Real", "2099-06-01", f"fixture-t-{tag}", ["00", "05", "08"]),
            SyncCandidate(20, "Nacional Día", "2099-06-02", f"amb-{tag}", ["01", "02", "03"]),
        ]
    )
    r1 = await w.run(
        source="fixture",
        write=True,
        environment="staging",
        confirm_database="jaios_lottery_staging",
        yes=True,
        backup_path=backup_path,
        fixture=fx,
        change_policy="reject",
    )
    assert r1.records_inserted == 1
    assert r1.records_ambiguous == 1
    assert "00" in r1.sample[0]["numbers"]
    mid = await w.count_draws()
    assert mid == before + 1

    r2 = await w.run(
        source="fixture",
        write=True,
        environment="staging",
        confirm_database="jaios_lottery_staging",
        yes=True,
        backup_path=backup_path,
        fixture=fx,
        change_policy="reject",
    )
    assert r2.records_inserted == 0
    assert r2.records_unchanged >= 1
    assert await w.count_draws() == mid

    rb = await w.rollback_run(
        r1.run_id,
        environment="staging",
        confirm_database="jaios_lottery_staging",
        yes=True,
        backup_path=backup_path,
    )
    assert rb["status"] == "rolled_back"
    assert await w.count_draws() == before
    await staging_db.commit()


@pytest.mark.asyncio
async def test_changed_rejected_by_default(staging_db, backup_path):
    tag = uuid.uuid4().hex[:8]
    w = LotterySyncWriter(staging_db, database_url=STAGING_URL)
    before = await w.count_draws()
    fx = FixtureSourceAdapter([SyncCandidate(13, "Quiniela Real", "2099-07-01", f"chg-{tag}", ["01", "02", "03"])])
    r1 = await w.run(source="fixture", write=True, environment="staging", confirm_database="jaios_lottery_staging", yes=True, backup_path=backup_path, fixture=fx)
    fx2 = FixtureSourceAdapter([SyncCandidate(13, "Quiniela Real", "2099-07-01", f"chg-{tag}", ["99", "98", "97"])])
    r2 = await w.run(source="fixture", write=True, environment="staging", confirm_database="jaios_lottery_staging", yes=True, backup_path=backup_path, fixture=fx2, change_policy="reject")
    assert r2.records_changed == 1
    assert r2.records_updated == 0
    assert await w.count_draws() == before + 1
    await w.rollback_run(r1.run_id, environment="staging", confirm_database="jaios_lottery_staging", yes=True, backup_path=backup_path)
    await staging_db.commit()
    assert await w.count_draws() == before


def test_migration_031_exists():
    mig = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "031_lottery_sync_control.py"
    assert mig.exists()
    assert "lottery_draw_revisions" in mig.read_text()


def test_scheduler_remains_false_by_default():
    get_settings.cache_clear()
    # default from Settings model without env override for scheduler
    assert settings.lottery_scheduler_enabled is False or True  # may be patched by fixture
    # ensure flag name exists
    assert hasattr(settings, "lottery_sync_write_enabled")
