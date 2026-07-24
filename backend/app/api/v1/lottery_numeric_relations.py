"""API — Auditoría y análisis del Motor de Relaciones Numéricas.

Toda la lógica delega en NumericRelationsService / analyze_observed_number.
No duplica fórmulas ni scoring.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.api.v1.lottery_ai_admin import require_ai_admin
from app.lottery.numeric_relations.api_schemas import (
    AnalyzeBody,
    enrich_table_rows,
    limit_from_body,
)
from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.db_history import analyze_from_db
from app.lottery.numeric_relations.service import NumericRelationsService
from app.models.lottery import LotteryLottery

router = APIRouter(
    prefix="/lottery/admin/numeric-relations",
    tags=["Lottery Numeric Relations"],
)

_PERMS = ("lottery_admin_ai", "lottery.admin", "lottery_admin_tools")


@router.get("/tables")
async def numeric_relations_tables(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """Tabla 1 y Tabla 2 completas (1..100), vistas separadas."""
    return {
        "table1": enrich_table_rows("table1"),
        "table2": enrich_table_rows("table2"),
        "range": {"min": 1, "max": 100},
        "source": "NumericRelationsService/catalog",
        "tables_are_separate": True,
    }


@router.get("/groups")
async def numeric_relations_groups(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """Agrupaciones separadas Tabla 1 / Tabla 2 (no mezclar)."""
    cat = build_catalog()
    t1 = {
        str(k): {"code": k, "numbers": v, "table": "table_1"}
        for k, v in sorted(cat.table1_code_to_numbers.items())
    }
    t2 = {
        str(k): {"code": k, "numbers": v, "table": "table_2"}
        for k, v in sorted(cat.table2_code_to_numbers.items())
    }
    return {
        "table1_groups": t1,
        "table2_groups": t2,
        "source": "NumericRelationsService/catalog",
        "tables_are_separate": True,
    }


@router.get("/comparative")
async def numeric_relations_comparative(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    svc = NumericRelationsService()
    return {"items": svc.comparative_table(), "source": "NumericRelationsService"}


@router.get("/lotteries")
async def numeric_relations_lotteries(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """Catálogo mínimo para el formulario de análisis (id/name/slug).

    Evita depender del listado ORM completo / defaults de IA cuando el esquema
    DEV aún no tiene todas las columnas 2.0/3.0.
    """
    rows = (
        await db.execute(
            select(LotteryLottery.id, LotteryLottery.name, LotteryLottery.slug)
            .where(LotteryLottery.is_aggregate.is_(False))
            .order_by(LotteryLottery.name.asc())
            .limit(300)
        )
    ).all()
    items = [
        {"id": str(UUID(str(r.id))), "name": r.name, "slug": r.slug}
        for r in rows
    ]
    return {"items": items, "source": "lottery_numeric_relations.lotteries"}


@router.post("/analyze")
async def numeric_relations_analyze(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    body: AnalyzeBody = Body(...),
) -> dict[str, Any]:
    """Análisis histórico — una sola implementación del motor."""
    try:
        limit = limit_from_body(body)
        result = await analyze_from_db(
            db,
            observed_number=body.observed_number,
            lottery_ids=list(body.lottery_ids),
            limit=limit,
        )
        payload = result.to_dict()
        all_matches: list[dict[str, Any]] = []
        zero_score: list[dict[str, Any]] = []
        for cand in payload.get("ranking") or []:
            all_matches.extend(cand.get("matches") or [])
            if int(cand.get("score") or 0) == 0:
                zero_score.append(cand)
        payload["matches"] = all_matches
        payload["companions_score_zero"] = zero_score
        payload["score"] = {
            "top": (payload.get("ranking") or [{}])[0] if payload.get("ranking") else None,
            "ranking_length": len(payload.get("ranking") or []),
        }
        payload["trace"] = {
            "match_traces": [m.get("trace") for m in all_matches if m.get("trace")],
            "candidate_traces": [
                c.get("trace") for c in (payload.get("ranking") or []) if c.get("trace")
            ],
        }
        engine_meta = dict(payload.get("analysis_metadata") or {})
        payload["metadata"] = {
            "engine": "lottery.numeric_relations",
            "llm_calculates": False,
            "exclude_observed_from_matches": True,
            "universe": "1..100",
            "occurrence_limit_explicit": limit.to_dict(),
            "tables_are_separate": True,
            **engine_meta,
        }
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
