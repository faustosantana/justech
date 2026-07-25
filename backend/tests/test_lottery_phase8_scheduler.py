"""Fase 8 — scheduler modes, automatic gates, circuit breaker, alerts."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings, settings
from app.models.lottery import LotteryDraw
from app.services.lottery_automatic_write_gates import (
    assert_automatic_write_gates,
    compute_lookback_range,
)
from app.services.lottery_circuit_breaker import evaluate_circuit, next_state_after_failure
from app.services.lottery_scheduler_service import LotterySchedulerService
from app.services.lottery_sync_service import SyncCandidate, SyncEnvironmentGuardError
from app.services.lottery_sync_writer import FixtureSourceAdapter, LotterySyncWriter

STAGING_URL = "postgresql+asyncpg://jaios_staging:jaios_staging_local_only@localhost:5434/jaios_lottery_staging"
BACKUP_DIR = Path(os.environ["LOTTERY_STAGING_BACKUP_DIR"]) if os.environ.get("LOTTERY_STAGING_BACKUP_DIR") else None


@pytest.fixture(autouse=True)
def _safe_defaults(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", False)
    monkeypatch.setattr(settings, "lottery_scheduler_mode", "disabled")
    monkeypatch.setattr(settings, "lottery_sync_enabled", False)
    monkeypatch.setattr(settings, "lottery_sync_write_enabled", False)
    monkeypatch.setattr(settings, "lottery_sync_automatic_write_enabled", False)
    monkeypatch.setattr(settings, "lottery_scraping_enabled", False)
    yield
    get_settings.cache_clear()


@pytest.fixture
def backup_path():
    if BACKUP_DIR is None or not BACKUP_DIR.is_dir():
        pytest.skip("set LOTTERY_STAGING_BACKUP_DIR for scheduler backup fixtures")
    files = sorted(BACKUP_DIR.glob("pre-phase*.dump"))
    if not files:
        pytest.skip("no staging backup")
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


def test_scheduler_disabled_default():
    assert settings.lottery_scheduler_enabled is False
    assert settings.lottery_scheduler_mode == "disabled"
    assert settings.lottery_sync_automatic_write_enabled is False


def test_lookback_range_timezone_day():
    start, end = compute_lookback_range(
        max_draw_date=date(2026, 7, 21),
        lookback_days=3,
        today=date(2026, 7, 22),
    )
    assert start == date(2026, 7, 18)
    assert end == date(2026, 7, 22)


def test_circuit_opens_after_failures():
    d = evaluate_circuit(state="closed", consecutive_failures=0)
    assert d.state == "closed" and d.allow_write
    ns = next_state_after_failure("closed", settings.lottery_sync_circuit_failure_threshold)
    assert ns == "open"
    d2 = evaluate_circuit(state="open", consecutive_failures=3, opened_at=datetime.now(timezone.utc))
    assert d2.allow_tick is False and d2.allow_write is False


def test_automatic_write_blocked_without_flags(backup_path):
    class R:
        records_new = 1
        records_changed = 0
        records_conflicted = 0
        records_invalid = 0
        records_ambiguous = 0

    with pytest.raises(SyncEnvironmentGuardError):
        assert_automatic_write_gates(
            database_url=STAGING_URL,
            mode="guarded_write",
            dry_run_report=R(),
            backup_path=backup_path,
            circuit_allow_write=True,
        )


def test_automatic_write_blocked_by_changed(backup_path, monkeypatch):
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", True)
    monkeypatch.setattr(settings, "lottery_scheduler_mode", "guarded_write")
    monkeypatch.setattr(settings, "lottery_sync_enabled", True)
    monkeypatch.setattr(settings, "lottery_sync_write_enabled", True)
    monkeypatch.setattr(settings, "lottery_sync_automatic_write_enabled", True)

    class R:
        records_new = 1
        records_changed = 2
        records_conflicted = 0
        records_invalid = 0
        records_ambiguous = 0

    with pytest.raises(SyncEnvironmentGuardError, match="CHANGED"):
        assert_automatic_write_gates(
            database_url=STAGING_URL,
            mode="guarded_write",
            dry_run_report=R(),
            backup_path=backup_path,
            circuit_allow_write=True,
        )


def test_automatic_write_blocked_wrong_port(backup_path, monkeypatch):
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", True)
    monkeypatch.setattr(settings, "lottery_scheduler_mode", "guarded_write")
    monkeypatch.setattr(settings, "lottery_sync_enabled", True)
    monkeypatch.setattr(settings, "lottery_sync_write_enabled", True)
    monkeypatch.setattr(settings, "lottery_sync_automatic_write_enabled", True)

    class R:
        records_new = 1
        records_changed = 0
        records_conflicted = 0
        records_invalid = 0
        records_ambiguous = 0

    bad = STAGING_URL.replace(":5434/", ":5433/")
    with pytest.raises(SyncEnvironmentGuardError):
        assert_automatic_write_gates(
            database_url=bad,
            mode="guarded_write",
            dry_run_report=R(),
            backup_path=backup_path,
            circuit_allow_write=True,
        )


@pytest.mark.asyncio
async def test_observe_fixture_no_write(staging_db, monkeypatch):
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", True)
    monkeypatch.setattr(settings, "lottery_scheduler_mode", "observe")
    svc = LotterySchedulerService(staging_db, database_url=STAGING_URL)
    await svc.set_mode("observe", enabled=True, by="test")
    before = int(await staging_db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    fixture = FixtureSourceAdapter(
        [
            SyncCandidate(
                source_id=13,
                lottery_name="Quiniela Real",
                draw_date="2099-06-01",
                source_reference="fixture-p8-observe",
                numbers=["00", "05", "11"],
            )
        ]
    )
    r1 = await svc.tick(fixture=fixture, force=True, initiated_by="test-observe")
    r2 = await svc.tick(fixture=fixture, force=True, initiated_by="test-observe")
    r3 = await svc.tick(fixture=fixture, force=True, initiated_by="test-observe")
    after = int(await staging_db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    assert r1.status in ("observe_ok", "blocked")
    assert r1.wrote is False and r2.wrote is False and r3.wrote is False
    assert after == before
    await staging_db.rollback()


@pytest.mark.asyncio
async def test_guarded_write_fixture_idempotent_rollback(staging_db, backup_path, monkeypatch):
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", True)
    monkeypatch.setattr(settings, "lottery_scheduler_mode", "guarded_write")
    monkeypatch.setattr(settings, "lottery_sync_enabled", True)
    monkeypatch.setattr(settings, "lottery_sync_write_enabled", True)
    monkeypatch.setattr(settings, "lottery_sync_automatic_write_enabled", True)

    svc = LotterySchedulerService(staging_db, database_url=STAGING_URL)
    await svc.set_mode(
        "guarded_write",
        enabled=True,
        confirmation="ENABLE GUARDED WRITE ON jaios_lottery_staging",
        by="test",
    )
    before = int(await staging_db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    tag = "p8gw"
    fixture = FixtureSourceAdapter(
        [
            SyncCandidate(
                source_id=13,
                lottery_name="Quiniela Real",
                draw_date="2099-06-02",
                source_reference=f"fixture-{tag}",
                numbers=["00", "05", "22"],
            )
        ]
    )
    r1 = await svc.tick(
        fixture=fixture, backup_path=backup_path, force=True, initiated_by="test-gw"
    )
    assert r1.status in ("guarded_write_ok", "blocked"), r1
    if r1.status == "blocked":
        pytest.skip(f"guarded write blocked: {r1.blocked_reason}")
    mid = int(await staging_db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    assert mid == before + 1
    assert r1.wrote is True and r1.write_run_id

    r2 = await svc.tick(
        fixture=fixture, backup_path=backup_path, force=True, initiated_by="test-gw-2"
    )
    after2 = int(await staging_db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    assert after2 == mid
    assert r2.metrics.get("inserted", 0) in (0, None) or r2.wrote is False or r2.metrics.get("new") == 0

    writer = LotterySyncWriter(staging_db, database_url=STAGING_URL)
    from uuid import UUID

    await writer.rollback_run(
        UUID(r1.write_run_id),
        environment="staging",
        confirm_database="jaios_lottery_staging",
        yes=True,
        backup_path=backup_path,
        initiated_by="test",
        via_scheduler=True,
    )
    await staging_db.commit()
    restored = int(await staging_db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    assert restored == before

    # disable flags path
    await svc.set_mode("disabled", enabled=False, by="test")
    await staging_db.commit()


@pytest.mark.asyncio
async def test_ambiguous_nacional_dia_no_insert(staging_db, monkeypatch):
    monkeypatch.setattr(settings, "lottery_scheduler_enabled", True)
    monkeypatch.setattr(settings, "lottery_scheduler_mode", "observe")
    svc = LotterySchedulerService(staging_db, database_url=STAGING_URL)
    await svc.set_mode("observe", enabled=True, by="test")
    before = int(await staging_db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    fixture = FixtureSourceAdapter(
        [
            SyncCandidate(
                source_id=20,
                lottery_name="Nacional Día",
                draw_date="2099-06-03",
                source_reference="fixture-nacional-dia",
                numbers=["01", "02", "03"],
            )
        ]
    )
    r = await svc.tick(fixture=fixture, force=True, initiated_by="test-amb")
    after = int(await staging_db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
    assert after == before
    assert r.wrote is False
    assert r.metrics.get("ambiguous", 0) >= 1 or "ambiguous_lottery" in r.alerts
    await staging_db.rollback()


@pytest.mark.asyncio
async def test_set_mode_requires_confirmation(staging_db):
    svc = LotterySchedulerService(staging_db, database_url=STAGING_URL)
    with pytest.raises(SyncEnvironmentGuardError):
        await svc.set_mode("guarded_write", enabled=True, confirmation="yes", by="test")
