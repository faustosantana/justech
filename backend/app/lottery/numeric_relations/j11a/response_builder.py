"""Response builder — merges engine facts + optional LLM prose."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.j11a.deterministic_fallback import deterministic_reply
from app.lottery.numeric_relations.j11a.guardrails import strip_win_probability_language
from app.lottery.numeric_relations.j11a.schemas import IntentResult, SessionMemory


def build_response(
    intent: IntentResult,
    memory: SessionMemory,
    tool_results: dict[str, Any],
    *,
    llm_text: str | None = None,
    explanation_level: str | None = None,
) -> dict[str, Any]:
    base = deterministic_reply(intent, memory, tool_results)
    prose = strip_win_probability_language(llm_text) if llm_text else None
    level = explanation_level or intent.explanation_level or memory.explanation_level

    analysis = None
    if "run_complete_analysis" in tool_results:
        analysis = tool_results["run_complete_analysis"].get("data")
    elif memory.last_result:
        analysis = memory.last_result

    return {
        "conversation_id": memory.conversation_id,
        "intent": intent.intent,
        "explanation_level": level,
        "message": prose or base,
        "deterministic_message": base,
        "llm_used": bool(prose),
        "analysis_id": memory.analysis_id,
        "primary_signal": memory.primary_signal,
        "alternatives": memory.alternatives,
        "observed_numbers": memory.observed_numbers,
        "actions": [
            "ver_evidencia",
            "ver_grafo",
            "ver_historico",
            "crear_seguimiento",
        ],
        "experimental": True,
        "disclaimer": (
            "EL MOTOR CALCULA. J-11A EXPLICA. "
            "Respaldo estructural ≠ probabilidad de ganar. "
            "No es recomendación de apuesta."
        ),
        "engine_snapshot": {
            "graph_complete_before_discovery": (analysis or {}).get(
                "graph_complete_before_discovery"
            ),
            "stages": (analysis or {}).get("stages_completed"),
        }
        if analysis
        else None,
    }
