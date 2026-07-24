"""J-3 — schemas and service wiring smoke (sin DB)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.lottery.numeric_relations.historical.api_schemas import (
    ConfirmationWindowBody,
    HistoricalSearchBody,
    LotteryScopeBody,
)
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode


def test_scope_defaults_follow_primary():
    pid = uuid4()
    scope = LotteryScopeBody(primary_lottery_ids=[pid])
    assert scope.confirming_lottery_ids == [pid]
    assert scope.follow_up_lottery_ids == [pid]


def test_search_body_range():
    pid = uuid4()
    body = HistoricalSearchBody(
        observed_number=34,
        scope=LotteryScopeBody(primary_lottery_ids=[pid]),
        confirmation_window=ConfirmationWindowBody(mode=ConfirmationWindowMode.SAME_DRAW),
        date_from=date(2015, 1, 1),
        date_to=date(2026, 12, 31),
        candidate=4,
    )
    assert body.observed_number == 34
    assert body.confirmation_window.timezone == "America/Santo_Domingo"
