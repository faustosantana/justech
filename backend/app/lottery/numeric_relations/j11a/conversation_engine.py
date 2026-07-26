"""J-11A Conversation Engine — interprets & explains; never calculates tables."""

from __future__ import annotations

from typing import Any, Callable

from app.lottery.numeric_relations.j11a.intent_engine import detect_intent
from app.lottery.numeric_relations.j11a.memory_engine import (
    get_or_create_session,
    update_from_analysis,
)
from app.lottery.numeric_relations.j11a.planner_engine import build_plan
from app.lottery.numeric_relations.j11a.response_builder import build_response
from app.lottery.numeric_relations.j11a.schemas import J11A_VERSION
from app.lottery.numeric_relations.j11a.tool_registry import call_tool


# Optional LLM synthesizer: (system, user) -> str | None
LlmFn = Callable[[str, str], str | None]


def _try_llm(llm: LlmFn | None, system: str, user: str) -> str | None:
    if llm is None:
        return None
    try:
        return llm(system, user)
    except Exception:
        return None


def chat(
    message: str,
    *,
    conversation_id: str | None = None,
    llm: LlmFn | None = None,
    date: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    memory = get_or_create_session(conversation_id)
    intent = detect_intent(message, memory)
    memory.last_question = message
    if intent.explanation_level:
        memory.explanation_level = intent.explanation_level

    plan = build_plan(intent, memory)
    tool_results: dict[str, Any] = {}

    if intent.needs_clarification and intent.intent != "FOLLOW_UP_CONTEXT":
        return build_response(intent, memory, tool_results)

    # Execute tools according to intent (deterministic)
    if intent.intent == "RUN_ANALYSIS":
        tool_results["run_complete_analysis"] = call_tool(
            "run_complete_analysis",
            numbers=intent.numbers,
            date=date or memory.analysis_date,
            mode=mode or memory.mode or "manual_reconstruido",
            explanation_level=memory.explanation_level,
        )
        data = tool_results["run_complete_analysis"].get("data")
        if data:
            update_from_analysis(memory, data)

    elif intent.intent in {"EXPLAIN_CANDIDATE", "FOLLOW_UP_CONTEXT", "EXPLAIN_CONFIDENCE"}:
        tool_results["get_analysis"] = call_tool("get_analysis", analysis_id=memory.analysis_id)
        if intent.candidate is not None:
            tool_results["get_candidate_evidence"] = call_tool(
                "get_candidate_evidence",
                candidate=intent.candidate,
                analysis_id=memory.analysis_id,
            )
            memory.last_candidate = intent.candidate

    elif intent.intent == "COMPARE_CANDIDATES":
        tool_results["get_candidate_ranking"] = call_tool(
            "get_candidate_ranking", analysis_id=memory.analysis_id
        )

    elif intent.intent == "SHOW_RELATIONSHIP_GRAPH":
        tool_results["get_relationship_graph"] = call_tool(
            "get_relationship_graph", analysis_id=memory.analysis_id
        )

    elif intent.intent == "SHOW_TABLE1_RELATIONS":
        n = (intent.numbers or memory.observed_numbers or [0])[0]
        tool_results["get_table1_family"] = call_tool("get_table1_family", number=n)

    elif intent.intent == "SHOW_TABLE2_RELATIONS":
        n = (intent.numbers or memory.observed_numbers or [0])[0]
        tool_results["get_table2_neighbors"] = call_tool("get_table2_neighbors", number=n)

    elif intent.intent == "SHOW_DERIVATIONS":
        tool_results["get_derivation_paths"] = call_tool(
            "get_derivation_paths", analysis_id=memory.analysis_id
        )

    elif intent.intent == "SHOW_ACTIVE_SIGNALS":
        tool_results["get_active_signals"] = call_tool("get_active_signals")

    elif intent.intent == "SHOW_FULFILLED_SIGNALS":
        tool_results["get_fulfilled_signals"] = call_tool("get_fulfilled_signals")

    elif intent.intent == "CHECK_HISTORICAL_APPEARANCE":
        cand = intent.candidate or memory.last_candidate
        if cand is not None:
            tool_results["get_historical_appearance"] = call_tool(
                "get_historical_appearance", candidate=cand
            )

    elif intent.intent == "RUN_BACKTEST":
        tool_results["run_backtest"] = call_tool("run_backtest")

    elif intent.intent == "SHOW_CHAIN":
        tool_results["get_chain_timeline"] = call_tool("get_chain_timeline")

    elif intent.intent == "SHOW_PREDICTIONS":
        tool_results["get_prediction_summary"] = call_tool("get_prediction_summary")

    system = (
        "Eres J-11A, copiloto analítico. EL MOTOR CALCULA; tú SOLO explicas. "
        "No inventes relaciones, fechas ni scores. No digas que un número va a salir. "
        "Usa solo los hechos del JSON del motor."
    )
    user = f"Pregunta: {message}\nHechos del motor: {tool_results}\nMemoria: {memory.to_dict()}"
    llm_text = _try_llm(llm, system, user)

    response = build_response(
        intent,
        memory,
        tool_results,
        llm_text=llm_text,
        explanation_level=memory.explanation_level,
    )
    response["plan"] = plan.to_dict()
    response["j11a_version"] = J11A_VERSION
    response["tool_results_keys"] = list(tool_results.keys())
    return response


def plan_only(message: str, conversation_id: str | None = None) -> dict[str, Any]:
    memory = get_or_create_session(conversation_id)
    intent = detect_intent(message, memory)
    return {
        "intent": intent.to_dict(),
        "plan": build_plan(intent, memory).to_dict(),
        "j11a_version": J11A_VERSION,
    }
