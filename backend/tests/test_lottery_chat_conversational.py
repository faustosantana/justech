"""Conversational chat intent — complete analysis + memory follow-ups."""

from __future__ import annotations

from app.services.lottery_ai_contracts import LotteryToolName
from app.services.lottery_chat_context import LotterySessionContext
from app.services.lottery_intent import resolve_intent
from app.lottery.ai.prompts.lottery_assistant_system_v1 import get_active_prompt


def test_analiza_el_35_runs_complete_analysis_without_wizard():
    r = resolve_intent("Analiza el 35.", LotterySessionContext())
    assert r.kind == "tool"
    assert r.tool == LotteryToolName.RUN_COMPLETE_ANALYSIS
    assert r.params["observed_number"] == 35
    assert r.clarify_message is None


def test_ese_numero_sin_contexto_pregunta():
    r = resolve_intent("Analiza ese número", LotterySessionContext())
    assert r.kind == "clarify"
    assert "número" in (r.clarify_message or "").lower()


def test_ese_numero_con_memoria_no_pregunta():
    ctx = LotterySessionContext(
        last_numbers=["35"],
        last_analysis={"type": "complete_analysis", "observed": 35, "primary": 54},
        current_primary_candidate=54,
    )
    r = resolve_intent("Analiza ese número", ctx)
    assert r.kind == "tool"
    assert r.tool == LotteryToolName.RUN_COMPLETE_ANALYSIS
    assert int(r.params["observed_number"]) == 35


def test_por_que_no_el_07_usa_memoria():
    ctx = LotterySessionContext(
        last_numbers=["35"],
        last_analysis={
            "type": "complete_analysis",
            "observed": 35,
            "primary": 54,
            "date": "2026-06-23",
        },
        current_primary_candidate=54,
    )
    r = resolve_intent("¿Por qué no el 07?", ctx)
    assert r.kind == "tool"
    assert r.tool == LotteryToolName.RUN_COMPLETE_ANALYSIS
    assert int(r.params["observed_number"]) == 35
    assert int(r.params["compare_with"]) == 7
    assert r.params["follow_up"] == "compare_rival"


def test_historico_follow_up():
    ctx = LotterySessionContext(
        last_numbers=["35"],
        last_analysis={"type": "complete_analysis", "observed": 35, "primary": 54},
        current_primary_candidate=54,
    )
    r = resolve_intent("¿Y qué dice el histórico?", ctx)
    assert r.kind == "tool"
    assert r.params.get("follow_up") == "historical"


def test_analiza_39_con_58():
    r = resolve_intent("Ahora analiza el 39 con el 58.", LotterySessionContext())
    assert r.kind == "tool"
    assert r.tool == LotteryToolName.RUN_COMPLETE_ANALYSIS
    assert int(r.params["observed_number"]) == 39
    assert int(r.params["confirmer"]) == 58


def test_system_prompt_v4_active_in_code_registry():
    p = get_active_prompt()
    assert p.version == "v4"
    assert "analista conversacional" in p.body.lower()
