"""Benchmarks: compound last-occurrence + default any position (Fase X.2)."""

from __future__ import annotations

from app.lottery.ai.compound_occurrence import (
    parse_compound_last_occurrence,
    resolve_effective_position,
)
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent


def test_resolve_default_any_position():
    pos, scope, ask = resolve_effective_position("¿Cuándo salió el 35 en Leidsa?")
    assert ask is False
    assert scope == "any_position"
    assert pos is None


def test_resolve_any_position_explicit():
    pos, scope, ask = resolve_effective_position(
        "¿Cuándo salió el 35 en Leidsa en cualquier posición?"
    )
    assert ask is False
    assert scope == "any_position"
    assert pos is None


def test_resolve_first_position_explicit():
    pos, scope, ask = resolve_effective_position(
        "¿Cuándo salió el 35 en Leidsa en primera posición?"
    )
    assert ask is False
    assert scope == "specific_position"
    assert pos == 1


def test_compound_leidsa_and_loteka():
    parsed = parse_compound_last_occurrence(
        "¿Cuándo salió el 35 en Leidsa y el 44 en Loteka?"
    )
    assert parsed is not None
    assert parsed["intent"] == "multi_last_occurrence"
    assert len(parsed["queries"]) == 2
    assert parsed["queries"][0]["number"] == "35"
    assert "Leidsa" in (parsed["queries"][0].get("lotteries") or [""])[0]
    assert parsed["queries"][1]["number"] == "44"
    assert parsed["queries"][0]["position"] is None
    assert parsed["queries"][1]["position"] is None


def test_compound_any_other_lottery_excludes_leidsa():
    parsed = parse_compound_last_occurrence(
        "¿Cuándo salió el 35 en Leidsa y el 44 en cualquier otra lotería?"
    )
    assert parsed is not None
    assert parsed["intent"] == "multi_last_occurrence"
    q1, q2 = parsed["queries"]
    assert q1["number"] == "35"
    assert q1["lotteries_scope"] == "named"
    assert q2["number"] == "44"
    assert q2["lotteries_scope"] == "all_except_previous"
    assert "Leidsa" in (q2.get("excluded_lotteries") or [])
    assert q1["position"] is None and q2["position"] is None


def test_intent_when_salió_not_frequency():
    ctx = LotterySessionContext(default_number_position_scope="any_position")
    intent = resolve_intent(
        "¿Cuándo salió el 35 en Leidsa y el 44 en cualquier otra lotería?", ctx
    )
    assert intent.kind == "tool"
    assert intent.tool == LotteryToolName.GET_LAST_OCCURRENCE
    assert intent.params.get("intent") == "multi_last_occurrence"
    assert len(intent.params.get("multi_queries") or []) == 2
    assert intent.tool != LotteryToolName.CALCULATE_FREQUENCIES


def test_single_leidsa_last_occurrence():
    ctx = LotterySessionContext()
    intent = resolve_intent("¿Cuándo salió el 35 en Leidsa?", ctx)
    assert intent.tool == LotteryToolName.GET_LAST_OCCURRENCE
    assert intent.params.get("number") in {"35", "035"} or str(intent.params.get("number")).endswith("35")
    assert intent.params.get("position") in (None, )


def test_any_position_intent():
    ctx = LotterySessionContext()
    intent = resolve_intent(
        "¿Cuándo salió el 35 en Leidsa en cualquier posición?", ctx
    )
    assert intent.tool == LotteryToolName.GET_LAST_OCCURRENCE
    assert intent.params.get("position") is None or intent.params.get("position_scope") == "any_position"


def test_same_day_not_multi_last():
    ctx = LotterySessionContext()
    intent = resolve_intent(
        "¿Han salido alguna vez el 55 y el 24 el mismo día?", ctx
    )
    assert intent.kind == "tool"
    assert intent.tool == LotteryToolName.GET_NUMBER_OCCURRENCES
    assert intent.params.get("relation") == "same_day"
    assert intent.params.get("numbers") == ["55", "24"]
    assert intent.params.get("position") is None
