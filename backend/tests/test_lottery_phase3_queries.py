"""Pruebas Fase 3 — consultas históricas contra jaios_lottery_dev."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.main import app
from app.services.lottery_aliases import (
    describe_alias_resolution,
    resolve_confirmed_source_id,
)
from app.services.lottery_exceptions import LotteryQueryError
from app.services.lottery_query_service import LotteryQueryService

DEV_URL = "postgresql+asyncpg://jaios:jaios_dev_local_only@localhost:5433/jaios_lottery_dev"


@pytest.fixture(autouse=True)
def _enable_module(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("LOTTERY_MODULE_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", DEV_URL)
    get_settings.cache_clear()
    # Patch settings object used by API
    from app.api.v1 import lottery as lottery_api
    from app import config

    config.get_settings.cache_clear()
    monkeypatch.setattr(lottery_api.settings, "lottery_module_enabled", True)
    yield
    get_settings.cache_clear()


@pytest.fixture
async def db_session():
    eng = create_async_engine(DEV_URL)
    Session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as session:
            yield session
    except Exception as exc:
        pytest.skip(f"lottery_dev no disponible: {exc}")
    finally:
        await eng.dispose()


def test_resolve_confirmed_aliases():
    assert resolve_confirmed_source_id("Real") == 13
    assert resolve_confirmed_source_id("Loteka") == 6
    assert resolve_confirmed_source_id("Leidsa") == 5
    assert resolve_confirmed_source_id("Nacional Noche") == 4
    assert resolve_confirmed_source_id("New York Día") == 16
    assert resolve_confirmed_source_id("New York Noche") == 17
    assert resolve_confirmed_source_id("Nacional Día") is None
    amb = describe_alias_resolution("Nacional Día")
    assert amb["ambiguous"] is True
    assert amb["resolved"] is False


@pytest.mark.asyncio
async def test_by_date_real_2022_03_15(db_session):
    svc = LotteryQueryService(db_session)
    res = await svc.by_date("Real", date(2022, 3, 15))
    assert res.meta.resolved_lottery is not None
    assert res.meta.resolved_lottery.source_id == 13
    assert res.total >= 1
    for draw in res.draws:
        assert draw.draw_date == date(2022, 3, 15)
        for n in draw.numbers:
            assert isinstance(n.number_value, str)
            # no raw_payload in response model
            assert not hasattr(draw, "raw_payload")


@pytest.mark.asyncio
async def test_following_days_vs_draws_differ(db_session):
    svc = LotteryQueryService(db_session)
    days = await svc.following_days("Real", date(2022, 3, 15), 7)
    draws = await svc.following_draws("Real", date(2022, 3, 15), 7)
    assert days.meta.query["semantics"] == "calendar_days"
    assert draws.meta.query["semantics"] == "next_n_draws"
    assert days.calendar_from == date(2022, 3, 16)
    assert days.calendar_to == date(2022, 3, 22)
    assert draws.total == 7 or draws.total <= 7
    # Not equivalent structures
    assert days.days_requested == 7
    assert draws.count_requested == 7
    assert set(type(x) for x in days.days_with_draws) == {date} or days.days_with_draws == []


@pytest.mark.asyncio
async def test_range_and_invalid(db_session):
    svc = LotteryQueryService(db_session)
    ok = await svc.range("Loteka", date(2022, 1, 1), date(2022, 1, 31), page=1, page_size=20)
    assert ok.pagination.page == 1
    with pytest.raises(LotteryQueryError) as exc:
        await svc.range("Loteka", date(2022, 2, 1), date(2022, 1, 1))
    assert exc.value.code == "RANGE_INVALID"


@pytest.mark.asyncio
async def test_number_zeros_and_frequencies(db_session):
    svc = LotteryQueryService(db_session)
    zeros = await svc.by_number("Real", "00", from_date=date(2022, 1, 1), to_date=date(2022, 12, 31))
    assert zeros.number == "00"
    for occ in zeros.occurrences:
        assert occ.number_value == "00"
    five = await svc.by_number("Real", "05", from_date=date(2022, 1, 1), to_date=date(2022, 6, 30), page_size=10)
    assert five.number == "05"
    freq = await svc.frequencies("Leidsa", date(2021, 1, 1), date(2021, 12, 31), limit=10)
    assert freq.total_observations > 0
    assert len(freq.items) <= 10


@pytest.mark.asyncio
async def test_repetitions_next_compare_cross(db_session):
    svc = LotteryQueryService(db_session)
    reps = await svc.repetitions("Real", date(2022, 3, 16), date(2022, 3, 22), min_count=2)
    assert reps.min_count == 2
    next_occ = await svc.next_occurrences("Real", "05", date(2022, 3, 15), limit=5)
    assert next_occ.note
    assert "predicción" in next_occ.note.lower() or "histórica" in next_occ.note.lower()
    cmp = await svc.compare(
        ["Real", "Nacional Noche"],
        date(2022, 3, 1),
        date(2022, 3, 31),
        "repeated_numbers",
        limit=20,
    )
    assert cmp.mode == "repeated_numbers"
    assert len(cmp.lotteries) == 2
    cross = await svc.cross_lottery(
        ["Real", "Nacional Noche"],
        date(2022, 3, 1),
        date(2022, 3, 15),
        "within_range",
    )
    assert cross.mode == "within_range"


@pytest.mark.asyncio
async def test_nacional_dia_pending(db_session):
    svc = LotteryQueryService(db_session)
    with pytest.raises(LotteryQueryError) as exc:
        await svc.by_date("Nacional Día", date(2022, 3, 15))
    assert exc.value.code == "LOTTERY_PENDING_MAPPING"


@pytest.mark.asyncio
async def test_api_by_date_auth_and_success():
    from app.api import deps
    from app.core.security import create_access_token

    token = create_access_token(subject=str(uuid.uuid4()), tenant_id=uuid.uuid4(), role="owner")
    fake_user = MagicMock()
    fake_user.is_superadmin = True
    fake_user.id = uuid.uuid4()
    fake_user.is_active = True

    async def _user():
        return fake_user

    async def _tenant():
        return None

    # Use real DB session from app — may fail if default DATABASE_URL wrong
    get_settings.cache_clear()
    import os

    os.environ["DATABASE_URL"] = DEV_URL
    os.environ["LOTTERY_MODULE_ENABLED"] = "true"
    get_settings.cache_clear()

    from app.db.session import get_db
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    eng = create_async_engine(DEV_URL)
    Session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async def _db():
        async with Session() as session:
            yield session

    app.dependency_overrides[deps.get_current_user] = _user
    app.dependency_overrides[deps.resolve_tenant_context] = _tenant
    app.dependency_overrides[get_db] = _db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            unauth = await client.get("/api/v1/lottery/results/by-date", params={"lottery": "Real", "date": "2022-03-15"})
            # Still has Authorization? without override path - we override user so might be 200
            # Test 401 without override
        app.dependency_overrides.pop(deps.get_current_user, None)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r401 = await client.get(
                "/api/v1/lottery/results/by-date",
                params={"lottery": "Real", "date": "2022-03-15"},
            )
            assert r401.status_code == 401

        app.dependency_overrides[deps.get_current_user] = _user
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r200 = await client.get(
                "/api/v1/lottery/results/by-date",
                params={"lottery": "Real", "date": "2022-03-15"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r200.status_code == 200
            body = r200.json()
            assert body["total"] >= 1
            assert "raw_payload" not in str(body)
    finally:
        app.dependency_overrides.clear()
        await eng.dispose()


def test_no_sql_string_concat_in_query_service():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "app" / "services" / "lottery_query_service.py"
    text = src.read_text(encoding="utf-8")
    assert "execute(f\"" not in text
    assert "text(f\"" not in text
