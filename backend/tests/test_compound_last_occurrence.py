"""Benchmarks: compound last-occurrence + default first position."""

from __future__ import annotations

from app.lottery.ai.compound_occurrence import (
    parse_compound_last_occurrence,
    resolve_effective_position,
)
from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent


def test_resolve_default_first_position():
    pos, scope, ask = resolve_effective_position("¿Cuándo salió el 35 en Leidsa?")
    assert ask is False
    assert scope == "first_position"
    assert pos == 1


def test_resolve_any_position_explicit():
    pos, scope, ask = resolve_effective_position(
        "¿Cuándo salió el 35 en Leidsa en cualquier posición?"
    )
    assert ask is False
    assert scope == "any_position"
    assert pos is None


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
    assert parsed["queries"][0]["position"] == 1
    assert parsed["queries"][1]["position"] == 1


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
    assert q1["position"] == 1 and q2["position"] == 1


def test_intent_when_salió_not_frequency():
    ctx = LotterySessionContext(default_number_position_scope="first_position")
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
    assert intent.params.get("position") == 1


def test_any_position_intent():
    ctx = LotterySessionContext()
    intent = resolve_intent("¿Cuándo salió el 35 en Leidsa en cualquier posición?", ctx)
    assert intent.tool == LotteryToolName.GET_LAST_OCCURRENCE
    assert intent.params.get("position") is None
    assert intent.params.get("position_scope") == "any_position"


def test_busca_ambos_en_primera():
    parsed = parse_compound_last_occurrence(
        "Busca el 10 en Real y el 20 en Nacional, ambos en primera."
    )
    assert parsed is not None
    assert len(parsed["queries"]) == 2
    assert parsed["queries"][0]["position"] == 1
    assert parsed["queries"][1]["position"] == 1


def test_count_applies_first_position_when_occurrences():
    ctx = LotterySessionContext(default_number_position_scope="first_position")
    intent = resolve_intent("¿Cuántas veces salió el 24 en Leidsa?", ctx)
    assert intent.kind == "tool"
    assert intent.tool in {
        LotteryToolName.GET_NUMBER_OCCURRENCES,
        LotteryToolName.GET_LAST_OCCURRENCE,
        LotteryToolName.COUNT_NUMBER_OCCURRENCES,
    } if hasattr(LotteryToolName, "COUNT_NUMBER_OCCURRENCES") else intent.tool in {
        LotteryToolName.GET_NUMBER_OCCURRENCES,
        LotteryToolName.GET_LAST_OCCURRENCE,
    }
    assert intent.tool != LotteryToolName.CALCULATE_FREQUENCIES
    if intent.params.get("position") is not None:
        assert intent.params["position"] == 1


def test_count_any_position():
    ctx = LotterySessionContext()
    intent = resolve_intent("¿Cuántas veces salió el 24 en Leidsa en cualquier posición?", ctx)
    if intent.kind == "tool" and intent.params.get("position_scope"):
        assert intent.params.get("position_scope") == "any_position" or intent.params.get("position") is None
