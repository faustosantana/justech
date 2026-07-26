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

    elif intent.intent == "INVESTIGATE":
        from app.lottery.numeric_relations.analysis_engine.scientific_validation.investigator import (
            investigator_answer,
        )
        from app.lottery.numeric_relations.analysis_engine.tiebreak_engine import (
            SELECTED_RULE_ID,
            DEFAULT_PRACTICAL_THRESHOLD,
        )
        import json
        from pathlib import Path

        inv = investigator_answer(message, numbers=intent.numbers or None)
        # Phase 3 tiebreak / prospective overlays
        low = message.lower()
        tb_path = Path("artifacts/tiebreak/final_benchmark.json")
        if not tb_path.exists():
            tb_path = (
                Path(__file__).resolve().parents[4]
                / "artifacts/tiebreak/final_benchmark.json"
            )
        if any(
            k in low
            for k in (
                "desempate",
                "tiebreak",
                "empatados",
                "14 errores",
                "motor anterior",
                "predicciones bloqueadas",
                "predicción bloqueada",
                "prediccion bloqueada",
                "prospectiv",
                "hash",
                "multi-fuerte",
                "multi fuerte",
                "integridad",
                "d+1",
                "source order",
                "perfil socio",
                "resultados pendientes",
                "predicción de hoy",
                "prediccion de hoy",
            )
        ):
            extra: dict = {
                "selected_rule": SELECTED_RULE_ID,
                "practical_threshold": DEFAULT_PRACTICAL_THRESHOLD,
            }
            if tb_path.exists():
                extra["benchmark"] = json.loads(tb_path.read_text(encoding="utf-8"))
            if "14" in low or "errores" in low:
                errp = Path("artifacts/tiebreak/error_cases.json")
                if errp.exists():
                    extra["error_cases_n"] = len(json.loads(errp.read_text(encoding="utf-8")))
            from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
                get_prospective_store,
            )

            store = get_prospective_store()
            if any(
                k in low
                for k in (
                    "bloquead",
                    "prospectiv",
                    "hash",
                    "multi",
                    "integridad",
                    "d+1",
                    "pendiente",
                    "hoy",
                    "métric",
                    "metric",
                    "source order",
                    "perfil",
                )
            ):
                extra["prospective"] = store.metrics()
                locked = [
                    p.to_dict()
                    for p in store.list()
                    if p.status in {"LOCKED", "AWAITING_RESULTS", "EVALUATED"}
                ]
                extra["locked"] = locked
                # J-11A never modifies locked predictions
                if "modificar" in low or "cambiar" in low or "editar" in low:
                    inv["message"] = (
                        "J-11A no puede modificar predicciones LOCKED. "
                        "Consulte auditoría y cree una nueva predicción si hace falta."
                    )
                elif "hash" in low:
                    hashes = [p.get("prediction_hash") for p in locked if p.get("prediction_hash")]
                    inv["message"] = f"Hashes de predicciones bloqueadas/evaluadas: {hashes}"
                elif "integridad" in low:
                    errs = extra["prospective"].get("total_integrity_errors")
                    inv["message"] = f"Errores de integridad en piloto: {errs}"
                elif "d+1" in low or "exactos" in low:
                    m = extra["prospective"]
                    inv["message"] = (
                        f"Exactos D+1 primary={m.get('primary_exact_d1')} "
                        f"multi={m.get('multi_strong_exact_d1')} "
                        f"(métricas persistidas; sin recalcular)."
                    )
                elif "source order" in low or "compara" in low:
                    inv["message"] = (
                        "Perfil operativo: socio + TIEBREAK_PROFILE_SOCIO_V1 + EMPATE_MULTI_FUERTE. "
                        "Source order es sombra y no altera la señal bloqueada. "
                        f"Comparación: {[{'id': p.prediction_id, 'shadow': bool(p.shadow_profiles)} for p in store.list()[-5:]]}"
                    )
                elif "multi" in low:
                    today_multi = [
                        {"id": p.prediction_id, "multi": p.multi_strong_candidates}
                        for p in store.list()
                        if p.multi_strong_candidates
                    ]
                    inv["message"] = f"Multi-fuertes registrados: {today_multi}"
                elif "pendiente" in low:
                    pending = [p.prediction_id for p in store.list() if p.status in {"LOCKED", "AWAITING_RESULTS"}]
                    inv["message"] = f"Predicciones pendientes de evaluación: {pending}"
                elif "bloquead" in low or "hoy" in low or "prospectiv" in low:
                    inv["message"] = (
                        f"Predicciones prospectivas (persistidas): {extra.get('prospective')}. "
                        "Una predicción LOCKED no se puede modificar ni recalcular."
                    )
                else:
                    inv["message"] = (
                        f"Métricas del piloto prospectivo: {extra.get('prospective')}"
                    )
            if "desempate" in low or ("regla" in low and "desempate" in low):
                inv["message"] = (
                    f"Regla de desempate operativa: {SELECTED_RULE_ID} "
                    f"(umbral práctico={DEFAULT_PRACTICAL_THRESHOLD}). "
                    "Se aplica solo tras el ranking; no rediscubre candidatos. "
                    "Si el empate estructural persiste → EMPATE_MULTI_FUERTE."
                )
            if "14" in low:
                bench = extra.get("benchmark") or {}
                o14 = bench.get("original_14") or {}
                inv["message"] = (
                    f"Los 14 errores Phase-2 están auditados. "
                    f"Baseline top1={((o14.get('baseline') or {}).get('top1_rate'))}, "
                    f"socio+multi top2={((o14.get('socio_multi') or {}).get('top2_rate'))}."
                )
            inv["tiebreak"] = extra
            tool_results["investigate_phase2"] = {"tool": "investigate_phase2", "data": inv}
        else:
            tool_results["investigate_phase2"] = {"tool": "investigate_phase2", "data": inv}

        response = build_response(
            intent,
            memory,
            tool_results,
            llm_text=None,
            explanation_level=memory.explanation_level,
        )
        response["message"] = inv.get("message") or response["message"]
        response["investigator"] = inv
        response["plan"] = plan.to_dict()
        response["j11a_version"] = J11A_VERSION
        response["tool_results_keys"] = list(tool_results.keys())
        return response

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
