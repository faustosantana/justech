"""J-11A typed tool registry — domain services only (no direct DB)."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.analysis_engine.backtest_engine import (
    manual_case_scenarios,
    run_backtest,
)
from app.lottery.numeric_relations.analysis_engine.case_engine import list_active_cases
from app.lottery.numeric_relations.analysis_engine.chain_engine import get_chain
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.prediction_engine import prediction_summary
from app.lottery.numeric_relations.analysis_engine.schemas import ExperimentalSignal
from app.lottery.numeric_relations.analysis_engine.signal_tracker import get_signal_store
from app.lottery.numeric_relations.j11a.schemas import J11A_VERSION


def _wrap(name: str, data: Any) -> dict[str, Any]:
    return {
        "tool": name,
        "version": J11A_VERSION,
        "engine_delegated": True,
        "data": data,
    }


def run_complete_analysis_tool(**kwargs: Any) -> dict[str, Any]:
    numbers = kwargs.get("numbers") or []
    result = run_complete_analysis(
        {
            "numbers": numbers,
            "date": kwargs.get("date"),
            "mode": kwargs.get("mode") or "manual_reconstruido",
            "positions": kwargs.get("positions") or ["first"],
            "derivation_depth": kwargs.get("derivation_depth", 2),
            "lotteries": kwargs.get("lotteries") or [],
            "create_signals": kwargs.get("create_signals", True),
            "explanation_level": kwargs.get("explanation_level") or "analitico",
        },
        persist=True,
    )
    return _wrap("run_complete_analysis", result.to_dict())


def get_analysis(analysis_id: str | None = None) -> dict[str, Any]:
    store = get_signal_store()
    if analysis_id and analysis_id in store.analyses:
        return _wrap("get_analysis", store.analyses[analysis_id])
    if store.analyses:
        last = next(reversed(store.analyses.values()))
        return _wrap("get_analysis", last)
    return _wrap("get_analysis", None)


def get_relationship_graph(analysis_id: str | None = None) -> dict[str, Any]:
    payload = get_analysis(analysis_id)["data"]
    return _wrap("get_relationship_graph", (payload or {}).get("graph"))


def get_candidate_evidence(candidate: int, analysis_id: str | None = None) -> dict[str, Any]:
    payload = get_analysis(analysis_id)["data"] or {}
    for c in payload.get("ranked_candidates") or []:
        if int(c["number"]) == int(candidate):
            return _wrap("get_candidate_evidence", c)
    return _wrap("get_candidate_evidence", None)


def get_candidate_ranking(analysis_id: str | None = None) -> dict[str, Any]:
    payload = get_analysis(analysis_id)["data"] or {}
    return _wrap("get_candidate_ranking", payload.get("ranked_candidates") or [])


def get_table1_family(number: int) -> dict[str, Any]:
    cat = build_catalog()
    comps = cat.get_table1_companions(int(number))
    return _wrap(
        "get_table1_family",
        {
            "mother_code": int(number),
            "companions": comps,
            "table": "table1",
            "note": "Compañeros T1 — no confundir con vecinos T2",
        },
    )


def get_table2_neighbors_tool(number: int) -> dict[str, Any]:
    cat = build_catalog()
    neigh = cat.get_table2_neighbors(int(number), exclude_self=True)
    return _wrap(
        "get_table2_neighbors",
        {
            "number": int(number),
            "neighbors": neigh,
            "table": "table2",
            "note": "Vecinos T2 — no son compañeros de Tabla 1",
        },
    )


def get_derivation_paths(analysis_id: str | None = None) -> dict[str, Any]:
    payload = get_analysis(analysis_id)["data"] or {}
    return _wrap("get_derivation_paths", payload.get("derivations") or [])


def get_active_signals() -> dict[str, Any]:
    store = get_signal_store()
    return _wrap("get_active_signals", [s.to_dict() for s in store.active_signals()])


def get_fulfilled_signals() -> dict[str, Any]:
    store = get_signal_store()
    fulfilled = [
        s.to_dict()
        for s in store.history_signals()
        if s.status.startswith("CUMPLIDO") or s.status == "CERRADO"
    ]
    return _wrap("get_fulfilled_signals", fulfilled)


def get_signal_status(signal_id: str | None = None, candidate: int | None = None) -> dict[str, Any]:
    store = get_signal_store()
    if signal_id and signal_id in store.signals:
        return _wrap("get_signal_status", store.signals[signal_id].to_dict())
    if candidate is not None:
        for s in store.signals.values():
            if s.number == int(candidate):
                return _wrap("get_signal_status", s.to_dict())
    return _wrap("get_signal_status", None)


def get_historical_relation_evidence(analysis_id: str | None = None) -> dict[str, Any]:
    payload = get_analysis(analysis_id)["data"] or {}
    hist = payload.get("historical_evidence")
    if not hist:
        return _wrap(
            "get_historical_relation_evidence",
            {
                "message": "No hay evidencia histórica adjunta a este análisis.",
                "hint": "Ejecute el análisis completo con histórico habilitado.",
            },
        )
    narr = hist.get("narrative") or {}
    metrics = hist.get("metrics") or {}
    return _wrap(
        "get_historical_relation_evidence",
        {
            "period": hist.get("period_label"),
            "date_from": hist.get("date_from"),
            "date_to": hist.get("date_to"),
            "exact_cases": metrics.get("exact_cases"),
            "exact_hits": metrics.get("exact_hits"),
            "t1_family_hits": metrics.get("t1_family_hits"),
            "t2_neighbor_hits": metrics.get("t2_neighbor_hits"),
            "d1_hits": metrics.get("d1_hits"),
            "d3_hits": metrics.get("d3_hits"),
            "d7_hits": metrics.get("d7_hits"),
            "evidence_quantity": metrics.get("evidence_quantity"),
            "comparison": hist.get("comparison") or narr.get("comparison"),
            "narrative": narr,
            "table1_priority": True,
            "note": "Exacto ≠ respaldo ampliado (familia T1 + vecinos T2).",
        },
    )


def get_historical_appearance(candidate: int) -> dict[str, Any]:
    """Only reports appearances already stored on signals — never invents dates."""
    store = get_signal_store()
    for s in store.signals.values():
        if s.number == int(candidate):
            return _wrap(
                "get_historical_appearance",
                {
                    "candidate": candidate,
                    "first_appearance_date": s.first_appearance_date,
                    "relative_day": s.relative_day,
                    "first_lottery": s.first_lottery,
                    "first_position": s.first_position,
                    "all_appearances": s.all_appearances,
                    "source": "signal_store",
                },
            )
    return _wrap(
        "get_historical_appearance",
        {
            "candidate": candidate,
            "first_appearance_date": None,
            "message": "No encontré evidencia suficiente en el motor para afirmar esa fecha histórica.",
        },
    )


def get_historical_profile(candidate: int) -> dict[str, Any]:
    ev = get_candidate_evidence(candidate)["data"]
    if not ev:
        return _wrap("get_historical_profile", None)
    return _wrap("get_historical_profile", ev.get("evidence", {}).get("historical_activations"))


def compare_candidates(a: int, b: int, analysis_id: str | None = None) -> dict[str, Any]:
    ra = get_candidate_evidence(a, analysis_id)["data"]
    rb = get_candidate_evidence(b, analysis_id)["data"]
    return _wrap(
        "compare_candidates",
        {
            "a": ra,
            "b": rb,
            "note": "Comparación basada en scores del motor; J-11A no recalcula.",
        },
    )


def compare_historical_cases() -> dict[str, Any]:
    return _wrap("compare_historical_cases", manual_case_scenarios())


def run_backtest_tool(**kwargs: Any) -> dict[str, Any]:
    scenarios = kwargs.get("scenarios") or manual_case_scenarios()
    return _wrap("run_backtest", run_backtest(scenarios, profile=kwargs.get("profile") or "manual_reconstruido"))


def get_chain_timeline(chain_id: str | None = None) -> dict[str, Any]:
    return _wrap("get_chain_timeline", get_chain(chain_id))


def get_prediction_summary_tool() -> dict[str, Any]:
    store = get_signal_store()
    return _wrap("get_prediction_summary", prediction_summary(store.active_signals()))


TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "run_complete_analysis": run_complete_analysis_tool,
    "get_analysis": get_analysis,
    "get_relationship_graph": get_relationship_graph,
    "get_candidate_evidence": get_candidate_evidence,
    "get_candidate_ranking": get_candidate_ranking,
    "get_table1_family": get_table1_family,
    "get_table2_neighbors": get_table2_neighbors_tool,
    "get_derivation_paths": get_derivation_paths,
    "get_active_signals": get_active_signals,
    "get_fulfilled_signals": get_fulfilled_signals,
    "get_signal_status": get_signal_status,
    "get_historical_appearance": get_historical_appearance,
    "get_historical_relation_evidence": get_historical_relation_evidence,
    "get_historical_profile": get_historical_profile,
    "compare_candidates": compare_candidates,
    "compare_historical_cases": compare_historical_cases,
    "run_backtest": run_backtest_tool,
    "get_chain_timeline": get_chain_timeline,
    "get_prediction_summary": get_prediction_summary_tool,
    "list_active_cases": lambda: _wrap("list_active_cases", list_active_cases()),
}


def call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    if name not in TOOL_REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    return TOOL_REGISTRY[name](**kwargs)
