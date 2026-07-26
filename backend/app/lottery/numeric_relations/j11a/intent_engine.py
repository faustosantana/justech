"""J-11A Intent Engine — deterministic intent detection (no math)."""

from __future__ import annotations

import re

from app.lottery.numeric_relations.j11a.schemas import INTENTS, IntentResult, SessionMemory
from app.lottery.numeric_relations.analysis_engine.schemas import ExplanationLevel


_NUM = re.compile(r"\b([1-9][0-9]?|100)\b")


def _extract_numbers(text: str) -> list[int]:
    vals = [int(x) for x in _NUM.findall(text)]
    # de-dup preserve order
    seen: set[int] = set()
    out: list[int] = []
    for v in vals:
        if 1 <= v <= 100 and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def detect_intent(message: str, memory: SessionMemory | None = None) -> IntentResult:
    text = (message or "").strip()
    low = text.lower()
    nums = _extract_numbers(text)
    mem = memory or SessionMemory(conversation_id="tmp")

    level = None
    if any(k in low for k in ("sencillo", "simple", "ejecutivo", "breve")):
        level = ExplanationLevel.EXECUTIVE.value
    elif any(k in low for k in ("técnico", "tecnico", "vista técnica", "trace")):
        level = ExplanationLevel.TECHNICAL.value
    elif any(k in low for k in ("completo", "analítico", "analitico", "análisis completo")):
        level = ExplanationLevel.ANALYTICAL.value

    # Investigator mode (Phase 2 scientific validation)
    if any(
        k in low
        for k in (
            "modo investigador",
            "qué regla",
            "que regla",
            "regla hizo ganar",
            "regla falla",
            "falla más",
            "falla mas",
            "errores del",
            "patrón nuevo",
            "patron nuevo",
            "descubriste",
            "mejor perfil",
            "segunda mejor",
            "calibración",
            "calibracion",
            "benchmark científico",
            "benchmark cientifico",
            "desempate",
            "tiebreak",
            "empatados",
            "14 errores",
            "predicción bloqueada",
            "prediccion bloqueada",
            "predicciones bloqueadas",
            "motor anterior",
        )
    ):
        return IntentResult(
            intent="INVESTIGATE",
            numbers=nums,
            candidate=nums[0] if nums else None,
            raw=text,
            explanation_level=level,
        )

    # Follow-up references
    if any(
        k in low
        for k in (
            "ese número",
            "ese numero",
            "el anterior",
            "el fuerte",
            "la segunda opción",
            "la segunda opcion",
            "los mismos números",
            "los mismos numeros",
            "y cuándo",
            "y cuando",
            "por qué quedó",
            "porque quedo",
            "¿y el",
            "y el ",
        )
    ) or low.startswith("¿y ") or low.startswith("y el"):
        cand = None
        if nums:
            cand = nums[0]
        elif "fuerte" in low and mem.primary_signal:
            cand = int(mem.primary_signal.get("number"))
        elif "segunda" in low and mem.alternatives:
            cand = int(mem.alternatives[0].get("number"))
        elif mem.last_candidate:
            cand = mem.last_candidate
        elif mem.primary_signal:
            cand = int(mem.primary_signal.get("number"))

        if "cuándo" in low or "cuando" in low or "salió" in low or "salio" in low:
            return IntentResult(
                intent="CHECK_HISTORICAL_APPEARANCE",
                numbers=nums,
                candidate=cand,
                raw=text,
                explanation_level=level,
            )
        if "por qué" in low or "porque" in low or "quedo fuerte" in low or "quedó fuerte" in low:
            return IntentResult(
                intent="EXPLAIN_CANDIDATE",
                numbers=list(mem.observed_numbers),
                candidate=cand,
                raw=text,
                explanation_level=level,
            )
        return IntentResult(
            intent="FOLLOW_UP_CONTEXT",
            numbers=list(mem.observed_numbers),
            candidate=cand,
            raw=text,
            explanation_level=level,
            needs_clarification=cand is None,
            clarification_prompt="¿Te refieres al fuerte principal, a una alternativa o a una señal activa?",
        )

    if any(k in low for k in ("backtest", "prueba histórica", "prueba historica")):
        return IntentResult(intent="RUN_BACKTEST", numbers=nums, raw=text, explanation_level=level)

    if any(k in low for k in ("cadena", "timeline", "seguimiento")):
        return IntentResult(intent="SHOW_CHAIN", numbers=nums, raw=text, explanation_level=level)

    if any(k in low for k in ("señales activas", "senales activas", "activos")):
        return IntentResult(intent="SHOW_ACTIVE_SIGNALS", raw=text, explanation_level=level)

    if any(k in low for k in ("cumplid", "historial de señales", "fulfilled")):
        return IntentResult(intent="SHOW_FULFILLED_SIGNALS", raw=text, explanation_level=level)

    if any(k in low for k in ("predicciones", "predicción de hoy", "predicciones de hoy")):
        return IntentResult(intent="SHOW_PREDICTIONS", numbers=nums, raw=text, explanation_level=level)

    if any(k in low for k in ("grafo", "graph", "relaciones completas")):
        return IntentResult(intent="SHOW_RELATIONSHIP_GRAPH", numbers=nums or list(mem.observed_numbers), raw=text, explanation_level=level)

    if "tabla 1" in low or "tabla1" in low:
        return IntentResult(intent="SHOW_TABLE1_RELATIONS", numbers=nums or list(mem.observed_numbers), raw=text, explanation_level=level)

    if "tabla 2" in low or "tabla2" in low:
        return IntentResult(intent="SHOW_TABLE2_RELATIONS", numbers=nums or list(mem.observed_numbers), raw=text, explanation_level=level)

    if "deriv" in low:
        return IntentResult(intent="SHOW_DERIVATIONS", numbers=nums or list(mem.observed_numbers), raw=text, explanation_level=level)

    if any(k in low for k in ("compar", "alternativa")):
        return IntentResult(
            intent="COMPARE_CANDIDATES",
            numbers=nums or list(mem.observed_numbers),
            candidate=nums[0] if nums else mem.last_candidate,
            raw=text,
            explanation_level=level,
        )

    if any(k in low for k in ("confianza", "respaldo estructural")):
        return IntentResult(
            intent="EXPLAIN_CONFIDENCE",
            numbers=list(mem.observed_numbers),
            candidate=nums[0] if nums else (int(mem.primary_signal["number"]) if mem.primary_signal else None),
            raw=text,
            explanation_level=level,
        )

    if any(k in low for k in ("analiza", "análisis", "analisis", "run analysis", "estudia")):
        if len(nums) < 1:
            return IntentResult(
                intent="CLARIFY",
                raw=text,
                needs_clarification=True,
                clarification_prompt="Indica los números observados a analizar (1..100).",
            )
        return IntentResult(intent="RUN_ANALYSIS", numbers=nums, raw=text, explanation_level=level)

    if any(k in low for k in ("por qué", "porque", "explica", "explicame", "explícame")):
        cand = nums[0] if nums else (int(mem.primary_signal["number"]) if mem.primary_signal else None)
        return IntentResult(
            intent="EXPLAIN_CANDIDATE",
            numbers=list(mem.observed_numbers),
            candidate=cand,
            raw=text,
            explanation_level=level,
            needs_clarification=cand is None,
            clarification_prompt="¿Qué candidato quieres que explique?",
        )

    # Default: if message is mostly numbers, run analysis
    if len(nums) >= 2 and len(text) < 40:
        return IntentResult(intent="RUN_ANALYSIS", numbers=nums, raw=text, explanation_level=level)

    return IntentResult(intent="UNKNOWN", numbers=nums, raw=text, explanation_level=level)


def assert_known_intents() -> None:
    assert set(INTENTS)
