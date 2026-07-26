"""Lottery IA dashboard aggregator — reuses Results + Pilot + freeze artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.lottery.numeric_relations.analysis_engine.motor_v1_freeze import motor_v1_freeze_manifest
from app.lottery.numeric_relations.analysis_engine.prospective_validation import (
    get_prospective_store,
)
from app.services.lottery_result_service import LotteryResultService


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _load_performance() -> dict[str, Any]:
    path = _repo_root() / "artifacts" / "tiebreak" / "final_benchmark.json"
    if not path.exists():
        return {
            "top1": None,
            "top2": None,
            "multi_fuerte": None,
            "source": None,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    test = data.get("test_socio_multi") or data.get("test_engine_integrated") or {}
    return {
        "top1": test.get("top1_or_multi_rate", test.get("top1_rate")),
        "top2": test.get("top2_rate"),
        "multi_fuerte": test.get("multi_fuerte_rate"),
        "source": "artifacts/tiebreak/final_benchmark.json#test_socio_multi",
        "label": "Phase 3 lab (test, socio+multi)",
    }


async def build_ia_dashboard(db: AsyncSession) -> dict[str, Any]:
    results_svc = LotteryResultService(db)
    sync = await results_svc.sync_status()
    pending = await results_svc.get_pending()
    latest = await results_svc.get_latest_n_dates(1, featured_only=True)
    last_row = latest[0] if latest else None

    # Pilot persistence is DEV/UAT-only; never crash Dashboard in Production.
    preds: list[dict[str, Any]] = []
    try:
        store = get_prospective_store()
        preds = [p.to_dict() for p in store.list()]
    except Exception:
        preds = []

    locked = sum(1 for p in preds if p.get("status") in {"LOCKED", "AWAITING_RESULTS"})
    evaluated = sum(1 for p in preds if p.get("status") == "EVALUATED")
    draft = sum(1 for p in preds if p.get("status") in {"DRAFT", "READY_TO_LOCK"})

    # Match last draw against evaluated predictions (best-effort, no recalculation)
    last_eval: dict[str, Any] | None = None
    if last_row and preds:
        for p in preds:
            if p.get("status") != "EVALUATED":
                continue
            ev = p.get("evaluation") or {}
            fr = p.get("future_result") or {}
            if fr.get("date") and last_row.get("date") and fr.get("date") != last_row.get("date"):
                continue
            primary = (p.get("primary_signal") or {}).get("number")
            multi = p.get("multi_strong_candidates") or []
            hit = bool(ev.get("is_exact_hit") or ev.get("hit_primary_exact") or ev.get("hit_multi_fuerte"))
            pred_nums = multi or ([primary] if primary is not None else [])
            last_eval = {
                "prediction_id": p.get("prediction_id"),
                "prediction": pred_nums,
                "estado": "Correcto" if hit else "Incorrecto",
                "hit_class": ev.get("hit_class"),
            }
            break
        if last_eval is None:
            for p in preds:
                if p.get("status") in {"LOCKED", "AWAITING_RESULTS"}:
                    if (p.get("target_date") or p.get("analysis_date")) == last_row.get("date"):
                        multi = p.get("multi_strong_candidates") or []
                        primary = (p.get("primary_signal") or {}).get("number")
                        last_eval = {
                            "prediction_id": p.get("prediction_id"),
                            "prediction": multi or ([primary] if primary is not None else []),
                            "estado": "Pendiente",
                            "hit_class": None,
                        }
                        break

    freeze = motor_v1_freeze_manifest()
    ultima_fecha = sync.get("last_draw_date") or (last_row or {}).get("date")
    return {
        "motor": {
            "estado": freeze["status"],
            "version": freeze["motor_version"],
            "perfil_activo": freeze["active_profile"],
            "tiebreak_activo": freeze["active_tiebreak"],
            "tiebreak": freeze.get("tiebreak"),
            "tiebreak_policy": freeze.get("tiebreak_policy"),
            "fecha_congelamiento": freeze["freeze_date"],
            "commit": freeze["engine_commit"],
            "release_tag": freeze.get("release_tag"),
            "engine_version": freeze["engine_version"],
            "read_only": True,
        },
        "resultados": {
            "ultima_actualizacion": sync.get("last_update"),
            "total_sorteos": sync.get("draws_count"),
            "total_loterias": sync.get("lotteries_count"),
            "featured_loterias": sync.get("featured_lotteries_count"),
            "pendientes_sincronizar": pending.get("pending_count"),
            "pendientes_detalle": pending.get("missing") or [],
            "ultima_fecha": ultima_fecha,
            "estado_sync": sync.get("state"),
        },
        "piloto": {
            "locked": locked,
            "evaluadas": evaluated,
            "pendientes": draft + locked,
            "draft": draft,
            "total": len(preds),
            "disponible": bool(preds) or locked or evaluated or draft,
        },
        "rendimiento": _load_performance(),
        "ultimo_sorteo": {
            "loteria": (last_row or {}).get("lottery"),
            "fecha": (last_row or {}).get("date"),
            "resultado": {
                "primera": (last_row or {}).get("primera"),
                "segunda": (last_row or {}).get("segunda"),
                "tercera": (last_row or {}).get("tercera"),
            }
            if last_row
            else None,
            "prediccion": (last_eval or {}).get("prediction"),
            "estado": (last_eval or {}).get("estado") or ("Sin predicción" if last_row else "—"),
            "prediction_id": (last_eval or {}).get("prediction_id"),
        },
        "freeze": freeze,
        "production_modified": False,
        "generated_for": "Lottery IA Dashboard",
    }
