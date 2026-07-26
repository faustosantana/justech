"""API — Auditoría y análisis del Motor de Relaciones Numéricas.

Toda la lógica delega en NumericRelationsService / analyze_observed_number.
No duplica fórmulas ni scoring.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.api.v1.lottery_ai_admin import require_ai_admin
from app.lottery.api_guards import enforce_nr_rate_limit, validate_lottery_id_count

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

async def _nr_rate_limit_dep(
    request: Request,
    response: Response,
    user: CurrentUser,
) -> None:
    enforce_nr_rate_limit(user_id=user.id, route=request.url.path, response=response)


router = APIRouter(
    prefix="/lottery/admin/numeric-relations",
    tags=["Lottery Numeric Relations"],
    dependencies=[Depends(_nr_rate_limit_dep)],
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
    validate_lottery_id_count(list(body.lottery_ids or []), field="lottery_ids")
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


@router.post("/validation-lab")
async def numeric_relations_validation_lab(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    body: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Motor Validation Lab — solo explicación. No modifica el motor ni las tablas."""
    from datetime import date as date_cls

    from app.lottery.numeric_relations.validation_lab import run_validation_lab

    try:
        observed = body.get("observations") or body.get("observed") or []
        if not isinstance(observed, list) or not observed:
            raise ValueError("observations requerido: lista de {number, lottery_name?}")
        manual = body.get("manual_fuerte")
        as_of = body.get("date") or body.get("as_of_date")
        as_of_date = date_cls.fromisoformat(str(as_of)) if as_of else None
        result = run_validation_lab(
            observed=observed,
            manual_fuerte=int(manual) if manual is not None else None,
            as_of_date=as_of_date,
        )
        result["requested_by"] = str(user.id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/historical-audit")
async def numeric_relations_historical_audit(
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    body: dict[str, Any] = Body(default={}),
) -> dict[str, Any]:
    """Historical Manual Logic Audit — read-only, reproducible, no motor/table writes."""
    from datetime import date as date_cls

    from app.lottery.numeric_relations.historical_audit_runner import (
        DEFAULT_DEV_DSN,
        load_precomputed_into_store,
        run_historical_audit,
    )
    from app.lottery.numeric_relations.historical_manual_audit import SEED_DEFAULT

    use_precomputed = bool(body.get("use_precomputed", True))
    if use_precomputed and not body.get("force_rerun"):
        pre = load_precomputed_into_store()
        if pre:
            return {
                "audit_id": pre["audit_id"],
                "trace_id": pre["trace_id"],
                "status": pre["status"],
                "progress": pre.get("progress"),
                "summary": pre.get("summary"),
                "source": "precomputed_evidence",
                "requested_by": str(user.id),
                "disclaimer": "Auditoría histórica; no es garantía predictiva.",
            }

    date_from = body.get("date_from")
    date_to = body.get("date_to")
    seed = int(body.get("seed") or SEED_DEFAULT)
    try:
        payload = await run_historical_audit(
            dsn=str(body.get("dsn") or DEFAULT_DEV_DSN),
            seed=seed,
            write_files=bool(body.get("write_files", False)),
            date_from=date_cls.fromisoformat(str(date_from)) if date_from else None,
            date_to=date_cls.fromisoformat(str(date_to)) if date_to else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "audit_id": payload["audit_id"],
        "trace_id": payload["trace_id"],
        "status": payload["status"],
        "progress": payload.get("progress"),
        "summary": payload.get("summary"),
        "source": "live_dev_readonly",
        "requested_by": str(user.id),
        "disclaimer": "Auditoría histórica; no es garantía predictiva.",
    }


@router.get("/historical-audit/four-year/summary")
async def numeric_relations_four_year_audit_summary(
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """Read-only four-year audit snapshot (precomputed evidence). Not predictive."""
    import json
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[4]
        / "artifacts/four_year_audit/statistics.json"
    )
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="four-year audit evidence missing; run scripts/run_four_year_seven_lottery_audit.py",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "audit_id": data.get("audit_id"),
        "trace_id": data.get("audit_id"),
        "status": "completed",
        "summary": data,
        "source": "precomputed_four_year_evidence",
        "production_forbidden": True,
        "requested_by": str(user.id),
        "disclaimer": "Auditoría histórica de 4 años; no es garantía predictiva.",
    }


@router.get("/historical-audit/{audit_id}")
async def numeric_relations_historical_audit_get(
    audit_id: str,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    from app.lottery.numeric_relations.historical_audit_runner import (
        get_audit,
        load_precomputed_into_store,
    )

    row = get_audit(audit_id)
    if not row:
        pre = load_precomputed_into_store()
        if pre and pre["audit_id"] == audit_id:
            row = pre
    if not row:
        raise HTTPException(status_code=404, detail="audit_id not found")
    return {
        "audit_id": row["audit_id"],
        "trace_id": row.get("trace_id"),
        "status": row.get("status"),
        "progress": row.get("progress"),
        "summary": row.get("summary"),
        "production_forbidden": True,
        "requested_by": str(user.id),
    }


@router.get("/historical-audit/{audit_id}/cases")
async def numeric_relations_historical_audit_cases(
    audit_id: str,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    verdict: str | None = Query(None),
) -> dict[str, Any]:
    from app.lottery.numeric_relations.historical_audit_runner import (
        get_audit,
        load_precomputed_into_store,
    )

    row = get_audit(audit_id)
    if not row:
        pre = load_precomputed_into_store()
        if pre and pre["audit_id"] == audit_id:
            row = pre
    if not row:
        raise HTTPException(status_code=404, detail="audit_id not found")
    cases = list(row.get("cases") or [])
    if verdict:
        cases = [c for c in cases if c.get("verdict") == verdict]
    total = len(cases)
    start = (page - 1) * page_size
    chunk = cases[start : start + page_size]
    return {
        "audit_id": audit_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "cases": chunk,
        "requested_by": str(user.id),
    }


@router.post("/historical-audit/{audit_id}/cancel")
async def numeric_relations_historical_audit_cancel(
    audit_id: str,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    from app.lottery.numeric_relations.historical_audit_runner import cancel_audit

    ok = cancel_audit(audit_id)
    if not ok:
        raise HTTPException(status_code=404, detail="audit_id not found")
    return {"audit_id": audit_id, "status": "cancelled", "requested_by": str(user.id)}


@router.get("/historical-audit/four-year/summary")
async def numeric_relations_four_year_audit_summary(
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """Read-only four-year audit snapshot (precomputed evidence). Not predictive."""
    import json
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[4]
        / "artifacts/four_year_audit/statistics.json"
    )
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="four-year audit evidence missing; run scripts/run_four_year_seven_lottery_audit.py",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "audit_id": data.get("audit_id"),
        "trace_id": data.get("audit_id"),
        "status": "completed",
        "summary": data,
        "source": "precomputed_four_year_evidence",
        "production_forbidden": True,
        "requested_by": str(user.id),
        "disclaimer": "Auditoría histórica de 4 años; no es garantía predictiva.",
    }
