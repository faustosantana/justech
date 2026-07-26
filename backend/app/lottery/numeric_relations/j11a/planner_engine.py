"""J-11A Planner — deterministic plan only; never computes Tabla 1/2."""

from __future__ import annotations

from app.lottery.numeric_relations.j11a.schemas import IntentResult, Plan, PlanStep, SessionMemory


def build_plan(intent: IntentResult, memory: SessionMemory | None = None) -> Plan:
    steps: list[PlanStep] = []
    n = 1

    def add(action: str, tool: str | None = None, **args: object) -> None:
        nonlocal n
        steps.append(PlanStep(step=n, action=action, tool=tool, args=dict(args)))
        n += 1

    if intent.intent == "RUN_ANALYSIS":
        add("Normalizar entradas")
        add("Definir posición (default first)")
        add("Ejecutar análisis completo", "run_complete_analysis", numbers=intent.numbers)
        add("Construir grafo (ya dentro del motor)")
        add("Recolectar evidencias")
        add("Descubrir candidatos")
        add("Rankear")
        add("Crear señal experimental")
        add("Generar explicación", "get_analysis")
    elif intent.intent == "EXPLAIN_CANDIDATE":
        add("Obtener análisis actual", "get_analysis")
        add("Obtener candidato", "get_candidate_evidence", candidate=intent.candidate)
        add("Obtener ranking", "get_candidate_ranking")
        add("Obtener rutas / componentes")
        add("Explicar sin recalcular scores")
    elif intent.intent == "COMPARE_CANDIDATES":
        add("Obtener ranking", "get_candidate_ranking")
        add("Comparar candidatos", "compare_candidates")
    elif intent.intent == "SHOW_RELATIONSHIP_GRAPH":
        add("Obtener grafo", "get_relationship_graph")
    elif intent.intent == "SHOW_TABLE1_RELATIONS":
        add("Consultar familia T1", "get_table1_family", numbers=intent.numbers)
    elif intent.intent == "SHOW_TABLE2_RELATIONS":
        add("Consultar vecinos T2", "get_table2_neighbors", numbers=intent.numbers)
    elif intent.intent == "SHOW_DERIVATIONS":
        add("Obtener derivaciones", "get_derivation_paths")
    elif intent.intent == "SHOW_ACTIVE_SIGNALS":
        add("Listar señales activas", "get_active_signals")
    elif intent.intent == "SHOW_FULFILLED_SIGNALS":
        add("Listar señales cumplidas", "get_fulfilled_signals")
    elif intent.intent == "CHECK_HISTORICAL_APPEARANCE":
        add("Identificar caso", "get_signal_status", candidate=intent.candidate)
        add("Consultar histórico", "get_historical_appearance", candidate=intent.candidate)
    elif intent.intent == "RUN_BACKTEST":
        add("Ejecutar backtest", "run_backtest")
    elif intent.intent == "SHOW_CHAIN":
        add("Obtener timeline", "get_chain_timeline")
    elif intent.intent == "SHOW_PREDICTIONS":
        add("Resumen de predicciones", "get_prediction_summary")
    elif intent.intent == "EXPLAIN_CONFIDENCE":
        add("Obtener candidato", "get_candidate_evidence", candidate=intent.candidate)
        add("Explicar confianza analítica (no probabilidad)")
    elif intent.intent == "INVESTIGATE":
        add("Cargar artefactos Fase 2", "investigate_phase2")
        add("Responder con evidencia empírica únicamente")
    elif intent.intent == "FOLLOW_UP_CONTEXT":
        add("Resolver referencia con memoria de sesión")
        add("Consultar motor / store", "get_analysis")
    else:
        add("Intent no reconocido — solicitar aclaración")

    return Plan(intent=intent.intent, steps=steps)
