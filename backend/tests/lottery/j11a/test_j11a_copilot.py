"""Tests — J-11A Analytical Copilot."""

from __future__ import annotations

import inspect

import pytest

from app.lottery.numeric_relations.analysis_engine.signal_tracker import reset_signal_store
from app.lottery.numeric_relations.j11a import chat, plan_only
from app.lottery.numeric_relations.j11a.conversation_engine import chat as chat_fn
from app.lottery.numeric_relations.j11a.guardrails import forbid_table_confusion_39_58_94
from app.lottery.numeric_relations.j11a.huawei_reuse import huawei_credential_status
from app.lottery.numeric_relations.j11a.intent_engine import detect_intent
from app.lottery.numeric_relations.j11a.memory_engine import reset_sessions
from app.lottery.numeric_relations.j11a.schemas import SessionMemory
from app.lottery.numeric_relations.j11a.tool_registry import TOOL_REGISTRY, call_tool


@pytest.fixture(autouse=True)
def _clean():
    reset_signal_store()
    reset_sessions()
    yield
    reset_signal_store()
    reset_sessions()


def test_j11a_never_calculates_tables():
    src = inspect.getsource(chat_fn)
    assert "calculate_table1_value" not in src
    assert "calculate_table2_value" not in src
    assert "generate_table1" not in src


def test_j11a_uses_complete_analysis_engine():
    assert "run_complete_analysis" in TOOL_REGISTRY
    out = chat("Analiza 35 y 14")
    assert out["primary_signal"]["number"] == 54
    assert out["engine_snapshot"]["graph_complete_before_discovery"] is True


def test_j11a_does_not_predict_without_engine_result():
    # Force unknown without numbers
    out = chat("predice el futuro sin datos")
    assert "predicción" not in out["message"].lower() or "sin resultados" in out.get("deterministic_message", "").lower() or out["intent"] in {"UNKNOWN", "CLARIFY", "SHOW_PREDICTIONS"}


def test_j11a_explains_35_14_54():
    chat("Analiza 35 y 14", conversation_id="c1")
    out = chat("¿Por qué quedó fuerte el 54?", conversation_id="c1")
    assert "54" in out["message"]
    assert "después de analizar" in out["message"].lower() or "respaldo" in out["message"].lower()


def test_j11a_explains_39_58_94_relation_types():
    out = chat("Analiza 39 y 58", conversation_id="c2")
    assert out["primary_signal"]["number"] == 94
    ev = call_tool("get_candidate_evidence", candidate=94)["data"]
    warns = forbid_table_confusion_39_58_94(ev)
    assert warns == []
    t1 = call_tool("get_table1_family", number=58)["data"]
    assert 94 not in t1["companions"]
    t2 = call_tool("get_table2_neighbors", number=58)["data"]
    assert 94 in t2["neighbors"]


def test_j11a_preserves_follow_up_context():
    chat("Analiza 35 y 14", conversation_id="c3")
    out = chat("¿Y el 54?", conversation_id="c3")
    assert out["observed_numbers"] == [35, 14]
    assert out["intent"] in {"FOLLOW_UP_CONTEXT", "EXPLAIN_CANDIDATE", "CHECK_HISTORICAL_APPEARANCE"}


def test_j11a_resolves_active_signal_reference():
    chat("Analiza 35 y 14", conversation_id="c4")
    out = chat("explícame el fuerte", conversation_id="c4")
    assert out["primary_signal"]["number"] == 54


def test_j11a_reports_missing_evidence():
    chat("Analiza 35 y 14", conversation_id="c5")
    out = chat("¿Por qué quedó fuerte el 99?", conversation_id="c5")
    assert "evidencia" in out["message"].lower() or "alternativa" in out["message"].lower() or "No encontré" in out["message"]


def test_j11a_does_not_invent_historical_dates():
    out = chat("Analiza 39 y 58", conversation_id="c6")
    hist = call_tool("get_historical_appearance", candidate=94)["data"]
    assert hist["first_appearance_date"] is None
    assert "evidencia" in (hist.get("message") or "evidencia").lower() or hist["first_appearance_date"] is None


def test_j11a_fallback_without_llm():
    out = chat("Analiza 35 y 14", llm=None)
    assert out["llm_used"] is False
    assert out["primary_signal"]["number"] == 54


def test_j11a_exposes_alternatives():
    out = chat("Analiza 49 y 44 y 70")
    assert isinstance(out["alternatives"], list)


def test_j11a_explanation_matches_evidence():
    out = chat("Analiza 39 y 58")
    ev = call_tool("get_candidate_evidence", candidate=94)["data"]["evidence"]
    assert 39 in ev["table1_sources"]
    assert 58 in ev["direct_confirmers"]
    assert "94" in out["message"] or out["primary_signal"]["number"] == 94


def test_huawei_credentials_are_reused():
    st = huawei_credential_status()
    assert st["duplicates_secrets"] is False
    assert st["j11a_calculates_tables"] is False
    assert "runtime_snapshot" in st["credentials_reused_from"]


def test_j11a_plan_is_deterministic():
    p = plan_only("Analiza 35 y 14")
    assert p["intent"]["intent"] == "RUN_ANALYSIS"
    assert p["plan"]["steps"]
    assert "run_complete_analysis" in {s.get("tool") for s in p["plan"]["steps"] if s.get("tool")}
