"""DEV/UAT daily prospective scheduler — never runs against Production."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.lottery.numeric_relations.analysis_engine.prospective.db import assert_not_production
from app.lottery.numeric_relations.analysis_engine.prospective.store import (
    ProspectiveStore,
    get_prospective_store,
)


def run_daily(
    *,
    store: ProspectiveStore | None = None,
    numbers: list[int] | None = None,
    analysis_date: str | None = None,
    target_date: str | None = None,
    lotteries: list[str] | None = None,
    positions: list[str] | None = None,
    auto_lock: bool = True,
    created_by: str = "scheduler",
    pilot_id: str | None = None,
) -> dict[str, Any]:
    """Create today's prospective prediction if inputs complete; skip duplicates."""
    assert_not_production()
    st = store or get_prospective_store()
    # pause check
    if pilot_id:
        pilot = st.get_pilot(pilot_id)
        if pilot and pilot.get("status") == "PAUSED":
            return {"ok": False, "reason": "PILOT_PAUSED"}
        if pilot and pilot.get("status") not in {"ACTIVE", "DRAFT", None}:
            if pilot.get("status") in {"COMPLETED", "CANCELLED"}:
                return {"ok": False, "reason": f"PILOT_{pilot['status']}"}

    day = analysis_date or date.today().isoformat()
    # duplicate guard: same analysis_date + same numbers
    existing = [
        p
        for p in st.list()
        if p.analysis_date == day
        and list(p.input_data.get("numbers") or []) == list(numbers or [])
        and p.status not in {"CANCELLED", "EXPIRED"}
    ]
    if existing:
        return {
            "ok": False,
            "reason": "DUPLICATE_DAILY_PREDICTION",
            "prediction_id": existing[0].prediction_id,
        }

    if not numbers:
        pred = st.create(
            {
                "numbers": [],
                "date": day,
                "target_date": target_date or (date.fromisoformat(day) + timedelta(days=1)).isoformat(),
                "mark_incomplete": True,
                "incomplete_reason": "INPUT_INCOMPLETE",
                "allow_incomplete": True,
                "created_by": created_by,
                "lotteries": lotteries,
                "positions": positions or ["first"],
            }
        )
        return {
            "ok": False,
            "reason": "INPUT_INCOMPLETE",
            "prediction_id": pred.prediction_id,
        }

    pred = st.create(
        {
            "numbers": numbers,
            "date": day,
            "target_date": target_date or (date.fromisoformat(day) + timedelta(days=1)).isoformat(),
            "lotteries": lotteries,
            "positions": positions or ["first"],
            "mode": "socio",
            "derivation_depth": 0,
            "created_by": created_by,
            "include_shadow": True,
        }
    )
    st.prepare_lock(pred.prediction_id)
    if auto_lock:
        pred = st.lock(pred.prediction_id, locked_by=created_by)
    metrics = st.metrics()
    st.save_snapshot(pilot_id, day, metrics)
    return {
        "ok": True,
        "prediction_id": pred.prediction_id,
        "status": pred.status,
        "hash": pred.prediction_hash,
        "multi_strong": pred.multi_strong_candidates,
        "primary": pred.primary_signal,
    }


def evaluate_pending(
    *,
    store: ProspectiveStore | None = None,
    results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate locked predictions against provided future results."""
    assert_not_production()
    st = store or get_prospective_store()
    results = results or []
    evaluated = []
    errors = []
    for pred in st.list():
        if pred.status not in {"LOCKED", "AWAITING_RESULTS"}:
            continue
        # match by target_date if present
        matched = None
        for r in results:
            if pred.target_date and r.get("date") and r["date"] != pred.target_date:
                # still allow D+n evaluation with any date after lock
                pass
            matched = r
            break
        if matched is None:
            continue
        try:
            out = st.evaluate(pred.prediction_id, matched)
            evaluated.append(out.prediction_id)
        except Exception as e:
            errors.append({"prediction_id": pred.prediction_id, "error": str(e)})
    return {"evaluated": evaluated, "errors": errors, "metrics": st.metrics()}
