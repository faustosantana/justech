"""API — Auditoría y análisis del Motor de Relaciones Numéricas.

Toda la lógica delega en NumericRelationsService / analyze_observed_number.
No duplica fórmulas ni scoring.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.api.v1.lottery_ai_admin import require_ai_admin

from app.lottery.numeric_relations.active_scope import (
    get_active_analysis_lotteries,
    get_archived_analysis_lotteries,
    resolve_active_scope_ids,
)
from app.lottery.numeric_relations.api_schemas import (
    AnalyzeBody,
    enrich_table_rows,
    limit_from_body,
    number_detail,
)
from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.db_history import analyze_from_db
from app.lottery.numeric_relations.service import NumericRelationsService

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
        "ui_columns_product": ["number", "code", "companions", "companion_count", "analyze"],
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


@router.get("/numbers/{n}")
async def numeric_relations_number_detail(
    n: int,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    table: str = Query("table1", pattern="^(table1|table2)$"),
) -> dict[str, Any]:
    """Detalle completo de un número en Tabla 1 o Tabla 2 (vistas separadas)."""
    try:
        return number_detail(n, table)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/export")
async def numeric_relations_export(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    table: str = Query("table1", pattern="^(table1|table2)$"),
    format: str = Query("json", pattern="^(json|csv)$"),
) -> dict[str, Any]:
    """Exportación técnica de auditoría (JSON o CSV como texto). Solo lectura."""
    rows = enrich_table_rows(table)
    if format == "json":
        return {
            "table": table,
            "format": "json",
            "count": len(rows),
            "items": rows,
            "read_only": True,
            "source": "NumericRelationsService/catalog",
        }
    # CSV textual (sin escribir archivo en disco)
    headers = [
        "number",
        "formula",
        "visible_value",
        "digits_without_point",
        "digit_count",
        "code",
        "literal_digit_sum",
        "group_numbers",
    ]
    lines = [",".join(headers)]
    for r in rows:
        group = ";".join(str(x) for x in (r.get("group_numbers") or []))
        lines.append(
            ",".join(
                [
                    str(r.get("number", "")),
                    f"\"{r.get('formula', '')}\"",
                    str(r.get("visible_value", "")),
                    str(r.get("digits_without_point", "")),
                    str(r.get("digit_count", "")),
                    str(r.get("code", "")),
                    str(r.get("literal_digit_sum", "")),
                    f"\"{group}\"",
                ]
            )
        )
    return {
        "table": table,
        "format": "csv",
        "count": len(rows),
        "csv": "\n".join(lines),
        "read_only": True,
        "source": "NumericRelationsService/catalog",
    }


@router.get("/lotteries")
async def numeric_relations_lotteries(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    scope: str = Query(
        "active",
        pattern="^(active|archived)$",
        description="active=is_featured (universo de producto); archived=histórico admin",
    ),
) -> dict[str, Any]:
    """Catálogo para formularios de análisis.

    Por defecto solo loterías activas (is_featured). Las archivadas requieren
    scope=archived (zona administrativa; no entran en cálculos activos).
    """
    if scope == "archived":
        lots = await get_archived_analysis_lotteries(db)
        label = "ARCHIVED"
        note = (
            "Esta fuente se conserva únicamente como histórico y no participa en los "
            "análisis, señales ni cálculos activos."
        )
    else:
        lots = await get_active_analysis_lotteries(db)
        label = "ACTIVE"
        note = "Análisis realizado con las loterías activas (destacadas) configuradas en el sistema."
    items = [{"id": x.id, "name": x.name, "slug": x.slug, "analysis_scope": label} for x in lots]
    return {
        "items": items,
        "count": len(items),
        "analysis_scope": label,
        "user_note": note,
        "source": "lottery_numeric_relations.lotteries.active_scope",
    }


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
        accepted, _active_used, scope_meta = await resolve_active_scope_ids(
            db, list(body.lottery_ids), require_non_empty=True
        )
        limit = limit_from_body(body)
        result = await analyze_from_db(
            db,
            observed_number=body.observed_number,
            lottery_ids=accepted,
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
            **scope_meta,
        }
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
