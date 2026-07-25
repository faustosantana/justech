"""Pre-J11A — rate limits y bounds NR (TD-003/006)."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response

from app.lottery.api_guards import (
    RateLimitExceeded,
    enforce_nr_rate_limit,
    reset_rate_limiter_for_tests,
    validate_date_range,
    validate_lottery_id_count,
    validate_nr_body_bounds,
    validate_numbers_list,
    validate_page_size,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_rate_limiter_for_tests()
    yield
    reset_rate_limiter_for_tests()


def test_date_range_allowed():
    validate_date_range(date(2020, 1, 1), date(2020, 3, 1), max_days=100)


def test_date_range_exceeded():
    with pytest.raises(HTTPException) as ei:
        validate_date_range(date(2000, 1, 1), date(2020, 1, 1), max_days=100)
    assert ei.value.status_code == 400
    assert "excede" in ei.value.detail.lower() or "máximo" in ei.value.detail.lower()


def test_date_from_after_to():
    with pytest.raises(HTTPException) as ei:
        validate_date_range(date(2021, 1, 1), date(2020, 1, 1))
    assert ei.value.status_code == 400


def test_date_to_without_from():
    with pytest.raises(HTTPException) as ei:
        validate_date_range(None, date(2020, 1, 1))
    assert ei.value.status_code == 400


def test_rate_limit_and_recovery():
    uid = uuid4()
    resp = Response()
    for _ in range(5):
        enforce_nr_rate_limit(
            user_id=uid, route="test.route", response=resp, limit_per_minute=5
        )
    with pytest.raises(RateLimitExceeded) as ei:
        enforce_nr_rate_limit(
            user_id=uid, route="test.route", response=resp, limit_per_minute=5
        )
    assert ei.value.status_code == 429
    assert "Retry-After" in (ei.value.headers or {})

    enforce_nr_rate_limit(
        user_id=uuid4(), route="test.route", response=Response(), limit_per_minute=5
    )

    reset_rate_limiter_for_tests()
    enforce_nr_rate_limit(
        user_id=uid, route="test.route", response=Response(), limit_per_minute=5
    )


def test_pagination_max(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "lottery_nr_max_page_size", 50)
    monkeypatch.setattr(settings, "lottery_nr_default_page_size", 20)
    assert validate_page_size(20) == 20
    with pytest.raises(HTTPException) as ei:
        validate_page_size(999)
    assert ei.value.status_code == 400


def test_lottery_count_and_numbers(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "lottery_nr_max_lotteries_per_request", 7)
    monkeypatch.setattr(settings, "lottery_nr_max_numbers_list", 5)
    validate_lottery_id_count([uuid4() for _ in range(7)])
    with pytest.raises(HTTPException):
        validate_lottery_id_count([uuid4() for _ in range(8)])
    validate_numbers_list([1, 35, 50])
    with pytest.raises(HTTPException):
        validate_numbers_list([1, 2, 3, 4, 5, 6])
    with pytest.raises(HTTPException):
        validate_numbers_list([0, 35])


def test_body_bounds_integration(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "lottery_nr_max_range_days", 100)
    monkeypatch.setattr(settings, "lottery_nr_max_lotteries_per_request", 7)
    monkeypatch.setattr(settings, "lottery_nr_max_numbers_list", 5)
    monkeypatch.setattr(settings, "lottery_nr_max_page_size", 50)
    body = SimpleNamespace(
        date_from=date.today() - timedelta(days=10),
        date_to=date.today(),
        scope=SimpleNamespace(
            primary_lottery_ids=[uuid4()],
            confirming_lottery_ids=[uuid4()],
            follow_up_lottery_ids=[uuid4()],
        ),
        candidates=[35, 50],
        page_size=20,
    )
    validate_nr_body_bounds(body)


def test_methodology_cases_numbers_still_valid():
    """35, 50, 86 permanecen en rango 1..100 — sin regresión de validación."""
    for n in (35, 50, 86):
        validate_numbers_list([n], field="observed")
