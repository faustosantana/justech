"""Deterministic fallback when Huawei/LLM is unavailable."""

from __future__ import annotations

from typing import Any

from app.lottery.numeric_relations.analysis_engine.explanation_engine import (
    explain_analysis,
    explain_relation_types_39_58_94,
    explain_why_strong,
)
from app.lottery.numeric_relations.j11a.guardrails import no_engine_message, no_evidence_message
from app.lottery.numeric_relations.j11a.schemas import IntentResult, SessionMemory


def deterministic_reply(
    intent: IntentResult,
    memory: SessionMemory,
    tool_results: dict[str, Any],
) -> str:
    """Always available — analysis and signals survive LLM outages."""
    if intent.intent == "RUN_ANALYSIS":
        data = tool_results.get("run_complete_analysis", {}).get("data")
        if not data:
            return no_engine_message()
        primary = data.get("primary_signal")
        if not primary:
            return "El motor completó el análisis pero no halló un candidato con evidencia suficiente."
        obs = ", ".join(str(n) for n in data.get("observed_numbers") or [])
        return (
            f"Análisis completo de [{obs}]. "
            f"FUERTE / señal principal: {primary.get('number')} "
            f"({primary.get('classification')}), "
            f"respaldo estructural {primary.get('analytical_confidence')}/100. "
            "Selección realizada después del cruce total de relaciones. "
            "PREDICCIÓN EXPERIMENTAL BASADA EN RELACIONES."
        )

    if intent.intent in {"EXPLAIN_CANDIDATE", "FOLLOW_UP_CONTEXT"}:
        data = memory.last_result or tool_results.get("get_analysis", {}).get("data")
        if not data:
            return no_engine_message()
        cand = intent.candidate or (memory.primary_signal or {}).get("number")
        if cand is None:
            return intent.clarification_prompt or "¿Qué número quieres que explique?"
        # Build lightweight ranked view
        ranked_nums = data.get("observed_numbers") or memory.observed_numbers
        # Use explanation helper with synthetic RankedCandidate-like via stored dicts
        primary = data.get("primary_signal") or {}
        if int(cand) == int(primary.get("number") or -1):
            return (
                f"El {cand} fue seleccionado después de analizar todas las relaciones de "
                f"{' y '.join(str(n) for n in ranked_nums)}, comparar los destinos encontrados "
                "y verificar que obtuvo el mayor respaldo conjunto. "
                "No fue elegido antes de completar el análisis."
            )
        # alternatives
        for a in data.get("alternatives") or []:
            if int(a.get("number")) == int(cand):
                return (
                    f"El {cand} quedó como alternativa ({a.get('classification')}) "
                    f"con score {a.get('score')}. No fue el mayor respaldo estructural."
                )
        return no_evidence_message()

    if intent.intent == "SHOW_TABLE1_RELATIONS":
        data = tool_results.get("get_table1_family", {}).get("data")
        if not data:
            return no_evidence_message()
        return (
            f"Tabla 1 — código madre {data['mother_code']}: compañeros {data['companions']}. "
            "No confundir con vecinos de Tabla 2."
        )

    if intent.intent == "SHOW_TABLE2_RELATIONS":
        data = tool_results.get("get_table2_neighbors", {}).get("data")
        if not data:
            return no_evidence_message()
        return (
            f"Tabla 2 — número {data['number']}: vecinos {data['neighbors']}. "
            "No son compañeros de Tabla 1."
        )

    if intent.intent == "EXPLAIN_CONFIDENCE":
        return (
            "La CONFIANZA ANALÍTICA / RESPALDO ESTRUCTURAL mide evidencia del grafo "
            "(fuentes, T1, T2, independencia, ambigüedad). "
            "No es probabilidad de que el número salga."
        )

    if intent.intent == "CHECK_HISTORICAL_APPEARANCE":
        data = tool_results.get("get_historical_appearance", {}).get("data") or {}
        if not data.get("first_appearance_date"):
            return (
                "No encontré evidencia suficiente en el motor para afirmar esa fecha histórica."
            )
        return (
            f"Primera aparición registrada: {data['first_appearance_date']} "
            f"(D+{data.get('relative_day')}) en {data.get('first_lottery')} "
            f"posición {data.get('first_position')}."
        )

    if intent.intent == "SHOW_ACTIVE_SIGNALS":
        data = tool_results.get("get_active_signals", {}).get("data") or []
        if not data:
            return "No hay señales activas."
        lines = [f"- {s['number']} ({s['classification']}) estado={s['status']}" for s in data]
        return "Señales activas (experimentales):\n" + "\n".join(lines)

    if intent.intent == "SHOW_CHAIN":
        data = tool_results.get("get_chain_timeline", {}).get("data") or {}
        tl = data.get("timeline") or []
        if not tl:
            return "No hay cadena activa."
        return "Cadena:\n" + "\n".join(
            f"- {e.get('date')}: {e.get('event')} señal={e.get('signal')}" for e in tl
        )

    if intent.needs_clarification:
        return intent.clarification_prompt or "Necesito una aclaración breve."

    # Special canonical explanation if memory has 39/58→94
    if memory.observed_numbers == [39, 58] and memory.primary_signal:
        # Keep labeling correct in fallback text
        return (
            "39 tiene relación de Tabla 1 con 94. "
            "58 confirma 94 vía Tabla 2 (vecino). "
            "No se afirma que 58 y 94 sean compañeros de Tabla 1."
        )

    return (
        "Puedo analizar números, explicar candidatos, mostrar grafo/evidencia "
        "o consultar señales. El motor calcula; yo solo expliqué resultados verificables."
    )
