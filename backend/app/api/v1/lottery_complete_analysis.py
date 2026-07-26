"""API — Complete Analysis Engine + J-11A (DEV). Does not touch Production deploy paths."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.lottery.numeric_relations.analysis_engine.backtest_engine import (
    manual_case_scenarios,
    run_backtest,
)
from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
    run_complete_analysis,
)
from app.lottery.numeric_relations.analysis_engine.signal_tracker import get_signal_store
from app.lottery.numeric_relations.j11a.conversation_engine import chat, plan_only
from app.lottery.numeric_relations.j11a.memory_engine import get_or_create_session

router = APIRouter(
    tags=["Complete Analysis Engine + J-11A"],
)


def _optional_huawei_llm():
    """Reuse existing Huawei/JAIOS credentials via LLMRouter — never duplicate secrets."""
    try:
        from app.lottery.ai.runtime import runtime_snapshot

        snap = runtime_snapshot()
        if not (snap.get("huawei_modelarts") or {}).get("credentials_present"):
            return None
        # Synthesis is optional; Conversation Engine always has deterministic fallback.
        # We do not open DB sessions from this thin adapter; callers that need LLM
        # prose should wire lottery_chat_service / LLMRouter with an existing session.
        return None
    except Exception:
        return None


@router.post("/analysis/run")
async def analysis_run(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        result = run_complete_analysis(body, persist=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return result.to_dict()


@router.get("/analysis/{analysis_id}")
async def analysis_get(analysis_id: str) -> dict[str, Any]:
    store = get_signal_store()
    data = store.analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    return data


@router.get("/analysis/{analysis_id}/graph")
async def analysis_graph(analysis_id: str) -> dict[str, Any]:
    data = await analysis_get(analysis_id)
    return data.get("graph") or {}


@router.get("/analysis/{analysis_id}/candidates")
async def analysis_candidates(analysis_id: str) -> dict[str, Any]:
    data = await analysis_get(analysis_id)
    return {"ranked_candidates": data.get("ranked_candidates") or []}


@router.get("/analysis/{analysis_id}/evidence")
async def analysis_evidence(analysis_id: str) -> dict[str, Any]:
    data = await analysis_get(analysis_id)
    return {
        "evidence_summary": data.get("evidence_summary"),
        "ranked_candidates": data.get("ranked_candidates"),
    }


@router.get("/analysis/{analysis_id}/derivations")
async def analysis_derivations(analysis_id: str) -> dict[str, Any]:
    data = await analysis_get(analysis_id)
    return {"derivations": data.get("derivations") or []}


@router.get("/signals/active")
async def signals_active() -> dict[str, Any]:
    store = get_signal_store()
    return {"signals": [s.to_dict() for s in store.active_signals()]}


@router.get("/signals/history")
async def signals_history() -> dict[str, Any]:
    store = get_signal_store()
    return {"signals": [s.to_dict() for s in store.history_signals()]}


@router.get("/signals/{signal_id}")
async def signals_get(signal_id: str) -> dict[str, Any]:
    store = get_signal_store()
    sig = store.get_signal(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="signal not found")
    return sig.to_dict()


@router.post("/signals/{signal_id}/evaluate")
async def signals_evaluate(signal_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    store = get_signal_store()
    try:
        d = body.get("date") or body.get("draw_date")
        if isinstance(d, str):
            d = date.fromisoformat(d[:10])
        sig = store.evaluate_signal(
            signal_id,
            draw_date=d,
            drawn_numbers=list(body.get("numbers") or body.get("drawn_numbers") or []),
            lottery=body.get("lottery"),
            position=body.get("position"),
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail="signal not found") from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return sig.to_dict()


@router.post("/backtest/run")
async def backtest_run(body: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    scenarios = body.get("scenarios") or manual_case_scenarios()
    profile = body.get("profile") or "manual_reconstruido"
    result = run_backtest(scenarios, profile=profile)
    store = get_signal_store()
    store.analyses[result["backtest_id"]] = result
    return result


@router.get("/backtest/{backtest_id}")
async def backtest_get(backtest_id: str) -> dict[str, Any]:
    store = get_signal_store()
    data = store.analyses.get(backtest_id)
    if not data:
        raise HTTPException(status_code=404, detail="backtest not found")
    return data


@router.post("/j11a/chat")
async def j11a_chat(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    use_llm = bool(body.get("use_llm", False))
    llm = _optional_huawei_llm() if use_llm else None
    return chat(
        str(body.get("message") or ""),
        conversation_id=body.get("conversation_id"),
        llm=llm,
        date=body.get("date"),
        mode=body.get("mode"),
    )


@router.post("/j11a/plan")
async def j11a_plan(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return plan_only(str(body.get("message") or ""), body.get("conversation_id"))


@router.post("/j11a/analyze")
async def j11a_analyze(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    numbers = body.get("numbers") or []
    msg = f"Analiza {' y '.join(str(n) for n in numbers)}"
    return chat(
        msg,
        conversation_id=body.get("conversation_id"),
        llm=None,
        date=body.get("date"),
        mode=body.get("mode"),
    )


@router.get("/j11a/conversations/{conversation_id}")
async def j11a_conversation(conversation_id: str) -> dict[str, Any]:
    mem = get_or_create_session(conversation_id)
    return mem.to_dict()


@router.get("/j11a/conversations/{conversation_id}/context")
async def j11a_context(conversation_id: str) -> dict[str, Any]:
    mem = get_or_create_session(conversation_id)
    return {
        "conversation_id": mem.conversation_id,
        "analysis_id": mem.analysis_id,
        "observed_numbers": mem.observed_numbers,
        "primary_signal": mem.primary_signal,
        "alternatives": mem.alternatives,
        "explanation_level": mem.explanation_level,
    }


@router.get("/j11a/analyses/{analysis_id}/explanation")
async def j11a_explanation(analysis_id: str) -> dict[str, Any]:
    store = get_signal_store()
    data = store.analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    return data.get("explanation") or {}


@router.post("/j11a/analyses/{analysis_id}/follow-up")
async def j11a_follow_up(analysis_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    store = get_signal_store()
    data = store.analyses.get(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="analysis not found")
    conv = body.get("conversation_id")
    mem = get_or_create_session(conv)
    from app.lottery.numeric_relations.j11a.memory_engine import update_from_analysis

    update_from_analysis(mem, data)
    return chat(str(body.get("message") or ""), conversation_id=mem.conversation_id, llm=None)


@router.get("/scientific/dashboard")
async def scientific_dashboard() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
        get_phase2_results,
    )

    data = get_phase2_results()
    if not data:
        raise HTTPException(status_code=404, detail="phase2 results not found — run validation pipeline")
    return data.get("dashboard") or data


@router.get("/scientific/summary")
async def scientific_summary() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
        get_phase2_results,
    )

    data = get_phase2_results()
    if not data:
        raise HTTPException(status_code=404, detail="phase2 results not found")
    # omit huge nested structures if present
    return {k: v for k, v in data.items() if k not in {"historical_rows"}}


@router.get("/scientific/rules")
async def scientific_rules() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
        get_phase2_results,
    )

    data = get_phase2_results()
    return data.get("rule_inventory") or {}


@router.get("/scientific/errors")
async def scientific_errors() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
        get_phase2_results,
    )

    data = get_phase2_results()
    return data.get("error_analysis") or {}


@router.get("/scientific/patterns")
async def scientific_patterns() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
        get_phase2_results,
    )

    data = get_phase2_results()
    return data.get("patterns") or {}


@router.get("/scientific/benchmark")
async def scientific_benchmark() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.scientific_validation.results_store import (
        get_phase2_results,
    )

    data = get_phase2_results()
    return data.get("benchmark") or {}


@router.post("/scientific/explain")
async def scientific_explain(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.scientific_validation.explainability import (
        explain_analysis_decisions,
    )

    numbers = body.get("numbers") or []
    if not numbers:
        raise HTTPException(status_code=400, detail="numbers required")
    return explain_analysis_decisions(
        list(numbers), mode=str(body.get("mode") or "socio"), date=body.get("date")
    )


@router.post("/scientific/run")
async def scientific_run(body: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    """DEV-only: run Phase 2 pipeline (can take minutes)."""
    from app.lottery.numeric_relations.analysis_engine.scientific_validation.pipeline import (
        run_phase2_pipeline,
    )

    limit = body.get("limit", 400)
    if limit is not None:
        limit = int(limit)
    result = run_phase2_pipeline(limit=limit, run_full_benchmark=bool(body.get("benchmark", True)))
    return {
        "ok": True,
        "dataset_counts": (result.get("dataset") or {}).get("counts"),
        "best_profile": (result.get("calibration") or {}).get("best_methodology_reproduction"),
        "best_variant": (result.get("benchmark") or {}).get("best_blind_variant"),
        "methodology_match_rate": (result.get("historical") or {}).get("methodology_match_rate"),
        "production_modified": False,
    }


@router.get("/tiebreak/summary")
async def tiebreak_summary() -> dict[str, Any]:
    import json
    from pathlib import Path

    for cand in (
        Path("artifacts/tiebreak/final_benchmark.json"),
        Path(__file__).resolve().parents[4] / "artifacts/tiebreak/final_benchmark.json",
    ):
        if cand.exists():
            return json.loads(cand.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="tiebreak artifacts not found — run tiebreak lab")


@router.get("/tiebreak/errors")
async def tiebreak_errors() -> dict[str, Any]:
    import json
    from pathlib import Path

    for cand in (
        Path("artifacts/tiebreak/error_cases.json"),
        Path(__file__).resolve().parents[4] / "artifacts/tiebreak/error_cases.json",
    ):
        if cand.exists():
            return {"cases": json.loads(cand.read_text(encoding="utf-8"))}
    raise HTTPException(status_code=404, detail="error_cases.json not found")


@router.post("/prospective-validation/predictions")
async def prospective_create(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    try:
        pred = get_prospective_store().create(body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return pred.to_dict()


@router.get("/prospective-validation/predictions")
async def prospective_list() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    return {"predictions": [p.to_dict() for p in get_prospective_store().list()]}


@router.get("/prospective-validation/predictions/{prediction_id}")
async def prospective_get(prediction_id: str) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    pred = get_prospective_store().get(prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="prediction not found")
    return pred.to_dict()


@router.post("/prospective-validation/predictions/{prediction_id}/prepare-lock")
async def prospective_prepare_lock(prediction_id: str) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    store = get_prospective_store()
    if not store.get(prediction_id):
        raise HTTPException(status_code=404, detail="prediction not found")
    try:
        return store.prepare_lock(prediction_id).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/prospective-validation/predictions/{prediction_id}/lock")
async def prospective_lock(prediction_id: str, body: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    store = get_prospective_store()
    if not store.get(prediction_id):
        raise HTTPException(status_code=404, detail="prediction not found")
    try:
        return store.lock(
            prediction_id, locked_by=(body or {}).get("locked_by")
        ).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/prospective-validation/predictions/{prediction_id}/evaluate")
async def prospective_evaluate(
    prediction_id: str, body: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    store = get_prospective_store()
    if not store.get(prediction_id):
        raise HTTPException(status_code=404, detail="prediction not found")
    try:
        return store.evaluate(prediction_id, body).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/prospective-validation/predictions/{prediction_id}/cancel")
async def prospective_cancel(
    prediction_id: str, body: dict[str, Any] | None = Body(None)
) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    store = get_prospective_store()
    if not store.get(prediction_id):
        raise HTTPException(status_code=404, detail="prediction not found")
    try:
        return store.cancel(prediction_id, (body or {}).get("reason")).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/prospective-validation/predictions/{prediction_id}/integrity")
async def prospective_integrity(prediction_id: str) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    store = get_prospective_store()
    if not store.get(prediction_id):
        raise HTTPException(status_code=404, detail="prediction not found")
    return store.check_integrity(prediction_id)


@router.get("/prospective-validation/predictions/{prediction_id}/audit-log")
async def prospective_audit_log(prediction_id: str) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    store = get_prospective_store()
    if not store.get(prediction_id):
        raise HTTPException(status_code=404, detail="prediction not found")
    return {"audit_log": store.audit_log(prediction_id)}


@router.post("/prospective-validation/run-daily")
async def prospective_run_daily(body: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective.scheduler import run_daily

    body = body or {}
    try:
        return run_daily(
            numbers=body.get("numbers"),
            analysis_date=body.get("analysis_date"),
            target_date=body.get("target_date"),
            lotteries=body.get("lotteries"),
            positions=body.get("positions"),
            auto_lock=bool(body.get("auto_lock", True)),
            created_by=body.get("created_by") or "api",
            pilot_id=body.get("pilot_id"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/prospective-validation/evaluate-pending")
async def prospective_evaluate_pending(body: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective.scheduler import (
        evaluate_pending,
    )

    body = body or {}
    return evaluate_pending(results=body.get("results") or [])


@router.get("/prospective-validation/metrics")
async def prospective_metrics() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    return get_prospective_store().metrics()


@router.get("/prospective-validation/comparison")
async def prospective_comparison() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    preds = get_prospective_store().list()
    return {
        "operational_policy": "perfil_socio + TIEBREAK_PROFILE_SOCIO_V1 + EMPATE_MULTI_FUERTE",
        "shadow_samples": [
            {
                "prediction_id": p.prediction_id,
                "operational_primary": (p.primary_signal or {}).get("number"),
                "operational_multi": p.multi_strong_candidates,
                "shadow": p.shadow_profiles,
            }
            for p in preds[-20:]
        ],
        "production_modified": False,
    }


@router.get("/prospective-validation/daily-snapshots")
async def prospective_daily_snapshots() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    return {"snapshots": get_prospective_store().list_snapshots()}


@router.post("/pilot/configurations")
async def pilot_create(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    return get_prospective_store().create_pilot(body)


@router.get("/pilot/configurations")
async def pilot_list() -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    return {"configurations": get_prospective_store().list_pilots()}


@router.get("/pilot/configurations/{pilot_id}")
async def pilot_get(pilot_id: str) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    p = get_prospective_store().get_pilot(pilot_id)
    if not p:
        raise HTTPException(status_code=404, detail="pilot not found")
    return p


@router.patch("/pilot/configurations/{pilot_id}")
async def pilot_patch(pilot_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    try:
        return get_prospective_store().patch_pilot(pilot_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/pilot/configurations/{pilot_id}/activate")
async def pilot_activate(pilot_id: str) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    try:
        return get_prospective_store().set_pilot_status(pilot_id, "ACTIVE")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/pilot/configurations/{pilot_id}/pause")
async def pilot_pause(pilot_id: str) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    try:
        return get_prospective_store().set_pilot_status(pilot_id, "PAUSED")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/pilot/configurations/{pilot_id}/complete")
async def pilot_complete(pilot_id: str) -> dict[str, Any]:
    from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
        get_prospective_store,
    )

    try:
        return get_prospective_store().set_pilot_status(pilot_id, "COMPLETED")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

