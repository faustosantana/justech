"""API J-3 — Analizador histórico T1↔T2. No modifica `/analyze` v1."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.api.v1.lottery_ai_admin import require_ai_admin
from app.lottery.numeric_relations.active_scope import (
    get_active_lottery_id_set,
    resolve_active_scope_ids,
)
from app.lottery.numeric_relations.historical.aggregates import HistoricalAggregatesService
from app.lottery.numeric_relations.historical.api_schemas import (
    CompareBody,
    HistoricalSearchBody,
    NumberOccurrenceDetailBody,
    NumberNextDrawsBody,
    NumberOccurrencesBody,
    NumberProfileBody,
    NumbersCompareBody,
    PatternDetailBody,
    WhyStrengthenedBody,
)
from app.lottery.numeric_relations.historical.db_universe import load_universe_from_db
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.number_explorer import NumberExplorerService
from app.lottery.numeric_relations.historical.service import HistoricalRelationsService
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION

router = APIRouter(
    prefix="/lottery/admin/numeric-relations/history",
    tags=["Lottery Numeric Relations History"],
)

_PERMS = ("lottery_admin_ai", "lottery.admin", "lottery_admin_tools")


def _scope_from_ids(
    primary: list[str],
    confirming: list[str],
    follow_up: list[str],
    names: dict[str, str],
) -> LotteryScope:
    return LotteryScope(
        primary_lottery_ids=tuple(primary),
        confirming_lottery_ids=tuple(confirming),
        follow_up_lottery_ids=tuple(follow_up),
        lottery_names=names,
    )


def _window_from_body(w) -> ConfirmationWindowConfig:
    try:
        return ConfirmationWindowConfig(
            mode=ConfirmationWindowMode(w.mode),
            timezone=w.timezone,
            hours_after=w.hours_after,
            next_k=w.next_k,
            session=w.session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _clamp_scope_ids(db: DbSession, body_scope) -> tuple[list[str], list[str], list[str], dict]:
    """Aplica universo activo (is_featured); ignora IDs no destacados."""
    primary_req = [str(x) for x in body_scope.primary_lottery_ids]
    confirming_req = [str(x) for x in (body_scope.confirming_lottery_ids or primary_req)]
    follow_req = [str(x) for x in (body_scope.follow_up_lottery_ids or primary_req)]
    primary, _active_used, meta = await resolve_active_scope_ids(
        db, primary_req, require_non_empty=True
    )
    all_active_ids = await get_active_lottery_id_set(db)
    confirming = [x for x in confirming_req if x in all_active_ids] or list(primary)
    follow_up = [x for x in follow_req if x in all_active_ids] or list(primary)
    rejected = set(meta.get("ignored_non_active_lottery_ids") or [])
    for raw in confirming_req + follow_req:
        if raw not in all_active_ids:
            rejected.add(raw)
    meta["ignored_non_active_lottery_ids"] = sorted(rejected)
    meta["ignored_non_active_count"] = len(rejected)
    meta["methodology_version"] = METHODOLOGY_VERSION
    return primary, confirming, follow_up, meta


async def _prepare(db: DbSession, body: HistoricalSearchBody | PatternDetailBody | CompareBody):
    try:
        primary, confirming, follow_up, scope_meta = await _clamp_scope_ids(db, body.scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    lids = sorted(set(primary) | set(confirming) | set(follow_up))
    try:
        universe, names = await load_universe_from_db(
            db,
            lottery_ids=lids,
            date_from=getattr(body, "date_from", None),
            date_to=getattr(body, "date_to", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    scope = _scope_from_ids(primary, confirming, follow_up, names)
    window = _window_from_body(body.confirmation_window)
    return universe, scope, window, names, scope_meta


async def _prepare_numbers(
    db: DbSession, body: NumberProfileBody | NumbersCompareBody | WhyStrengthenedBody | NumberOccurrencesBody
):
    try:
        primary, confirming, follow_up, scope_meta = await _clamp_scope_ids(db, body.scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    lids = sorted(set(primary) | set(confirming) | set(follow_up))
    try:
        universe, names = await load_universe_from_db(
            db,
            lottery_ids=lids,
            date_from=getattr(body, "date_from", None),
            date_to=getattr(body, "date_to", None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    scope = _scope_from_ids(primary, confirming, follow_up, names)
    window = _window_from_body(body.confirmation_window)
    return universe, scope, window, names, scope_meta


def _with_scope_meta(out: dict[str, Any], scope_meta: dict[str, Any]) -> dict[str, Any]:
    out = dict(out)
    out["analysis_scope_meta"] = scope_meta
    out.setdefault("analysis_scope", scope_meta.get("analysis_scope"))
    out.setdefault("active_lottery_count", scope_meta.get("active_lottery_count"))
    return out


@router.post("/conditions/search")
async def search_conditions(
    body: HistoricalSearchBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """1. Buscar condiciones históricas (eventos atómicos + combinaciones + tasas)."""
    universe, scope, window, _names, scope_meta = await _prepare(db, body)
    svc = HistoricalRelationsService(universe=universe)
    result = svc.search_conditions(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        candidate=body.candidate,
        confirmer=body.confirmer,
        max_horizon=body.max_horizon,
    )
    if body.min_sample is not None:
        result["combination_events"] = [
            e
            for e in result["combination_events"]
            # filter patterns later via aggregates; keep events, annotate
        ]
        result["min_sample_filter"] = body.min_sample
    result["ai_conclusions"] = None  # never invent
    return _with_scope_meta(result, scope_meta)


@router.post("/posterior/summary")
async def posterior_summary(
    body: HistoricalSearchBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """2. Resumen posterior / ciclos / tasas por horizonte."""
    universe, scope, window, _, scope_meta = await _prepare(db, body)
    svc = HistoricalRelationsService(universe=universe)
    full = svc.search_conditions(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        candidate=body.candidate,
        confirmer=body.confirmer,
        max_horizon=body.max_horizon,
    )
    return _with_scope_meta({
        "methodology_version": METHODOLOGY_VERSION,
        "effective_parameters": full["effective_parameters"],
        "statistics": full["statistics"],
        "candidate_ranking_by_confirmations": full["candidate_ranking_by_confirmations"],
        "combination_event_count": full["combination_event_count"],
        "atomic_event_count": full["atomic_event_count"],
        "ai_conclusions": None,
    },
        scope_meta,
    )


@router.post("/combinations")
async def combinations(
    body: HistoricalSearchBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """3. Combinaciones N-C-{V} + pares/tríos."""
    universe, scope, window, _, scope_meta = await _prepare(db, body)
    agg = HistoricalAggregatesService(universe=universe)
    out = agg.compute(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        candidate=body.candidate,
        confirmer=body.confirmer,
        include_pairs_triples=body.include_pairs_triples,
        max_horizon=body.max_horizon,
    )
    patterns = out["combination_patterns"]
    if body.min_sample is not None:
        patterns = [p for p in patterns if p["event_count"] >= int(body.min_sample)]
    return _with_scope_meta({
        "methodology_version": METHODOLOGY_VERSION,
        "effective_parameters": out["effective_parameters"],
        "combination_patterns": patterns,
        "totals": out["totals"],
        "ai_conclusions": None,
    },
        scope_meta,
    )


@router.post("/matrix")
async def matrix(
    body: HistoricalSearchBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """4. Matriz candidato × confirmador."""
    universe, scope, window, _, scope_meta = await _prepare(db, body)
    agg = HistoricalAggregatesService(universe=universe)
    out = agg.compute(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        candidate=body.candidate,
        confirmer=body.confirmer,
        max_horizon=body.max_horizon,
    )
    return _with_scope_meta({
        "methodology_version": METHODOLOGY_VERSION,
        "effective_parameters": out["effective_parameters"],
        "matrix": out["matrix"],
        "ai_conclusions": None,
    },
        scope_meta,
    )


@router.post("/patterns/detail")
async def pattern_detail(
    body: PatternDetailBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """5. Detalle de patrón atómico o combinación + evidencia."""
    universe, scope, window, _, scope_meta = await _prepare(db, body)
    confirmer = body.confirmer
    if body.confirmers:
        # combination detail: filter candidate; match confirmers set
        agg = HistoricalAggregatesService(universe=universe)
        out = agg.compute(
            observed_number=body.observed_number,
            scope=scope,
            window=window,
            date_from=body.date_from,
            date_to=body.date_to,
            candidate=body.candidate,
            max_horizon=body.max_horizon,
        )
        key = ",".join(str(x) for x in sorted({int(x) for x in body.confirmers}))
        matches = [
            p
            for p in out["combination_patterns"]
            if p["candidate"] == body.candidate and p["confirmers_key"] == key
        ]
        svc = HistoricalRelationsService(universe=universe)
        full = svc.search_conditions(
            observed_number=body.observed_number,
            scope=scope,
            window=window,
            date_from=body.date_from,
            date_to=body.date_to,
            candidate=body.candidate,
            max_horizon=body.max_horizon,
        )
        evidence = [
            e
            for e in full["combination_events"]
            if e["candidate"] == body.candidate and e["confirmers_key"] == key
        ]
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "pattern_level": "combination",
            "pattern": matches[0] if matches else None,
            "evidence": evidence,
            "effective_parameters": out["effective_parameters"],
            "ai_conclusions": None,
        }

    if confirmer is None:
        raise HTTPException(status_code=400, detail="confirmer or confirmers required")

    agg = HistoricalAggregatesService(universe=universe)
    out = agg.compute(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        candidate=body.candidate,
        confirmer=confirmer,
        max_horizon=body.max_horizon,
    )
    matches = [
        p
        for p in out["atomic_patterns"]
        if p["candidate"] == body.candidate and p["confirmer"] == confirmer
    ]
    svc = HistoricalRelationsService(universe=universe)
    full = svc.search_conditions(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        candidate=body.candidate,
        confirmer=confirmer,
        max_horizon=body.max_horizon,
    )
    return _with_scope_meta({
        "methodology_version": METHODOLOGY_VERSION,
        "pattern_level": "atomic",
        "pattern": matches[0] if matches else None,
        "evidence": full["atomic_events"],
        "effective_parameters": out["effective_parameters"],
        "ai_conclusions": None,
    },
        scope_meta,
    )


@router.post("/evidence/by-draw")
async def evidence_by_draw(
    body: HistoricalSearchBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """6. Evidencia agrupada por draw_id ancla."""
    universe, scope, window, _, scope_meta = await _prepare(db, body)
    svc = HistoricalRelationsService(universe=universe)
    full = svc.search_conditions(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        candidate=body.candidate,
        confirmer=body.confirmer,
        max_horizon=body.max_horizon,
    )
    by_draw: dict[str, Any] = {}
    for e in full["combination_events"]:
        did = e["anchor"]["draw_id"]
        by_draw.setdefault(
            did,
            {"anchor": e["anchor"], "combinations": [], "atomics": []},
        )
        by_draw[did]["combinations"].append(e)
    for e in full["atomic_events"]:
        did = e["anchor"]["draw_id"]
        by_draw.setdefault(
            did,
            {"anchor": e["anchor"], "combinations": [], "atomics": []},
        )
        by_draw[did]["atomics"].append(e)
    return _with_scope_meta({
        "methodology_version": METHODOLOGY_VERSION,
        "effective_parameters": full["effective_parameters"],
        "by_draw_id": by_draw,
        "ai_conclusions": None,
    },
        scope_meta,
    )


@router.post("/cycles")
async def cycles(
    body: HistoricalSearchBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """7. Ciclos + censura."""
    universe, scope, window, _, scope_meta = await _prepare(db, body)
    svc = HistoricalRelationsService(universe=universe)
    full = svc.search_conditions(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        candidate=body.candidate,
        confirmer=body.confirmer,
        max_horizon=body.max_horizon,
    )
    return _with_scope_meta({
        "methodology_version": METHODOLOGY_VERSION,
        "effective_parameters": full["effective_parameters"],
        "cycles": full["statistics"]["cycles"],
        "response_rates": full["statistics"]["response_rates"],
        "terminology": full["statistics"]["terminology"],
        "ai_conclusions": None,
    },
        scope_meta,
    )


@router.post("/compare")
async def compare(
    body: CompareBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """8–9. Comparar candidatos / confirmadores / combinaciones / loterías."""
    universe, scope, window, _, scope_meta = await _prepare(db, body)
    agg = HistoricalAggregatesService(universe=universe)
    out = agg.compute(
        observed_number=body.observed_number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        max_horizon=body.max_horizon,
    )
    mode = body.compare_mode
    if mode == "candidates":
        wanted = set(body.candidates) or {p["candidate"] for p in out["atomic_patterns"]}
        items = []
        for cand in sorted(wanted):
            related = [p for p in out["atomic_patterns"] if p["candidate"] == cand]
            items.append(
                {
                    "candidate": cand,
                    "patterns": related,
                    "total_events": sum(p["event_count"] for p in related),
                }
            )
        items.sort(key=lambda x: -x["total_events"])
        return _with_scope_meta(
            {"methodology_version": METHODOLOGY_VERSION, "compare_mode": mode, "items": items, "ai_conclusions": None},
            scope_meta,
        )

    if mode == "confirmers":
        wanted = set(body.confirmers) or {p["confirmer"] for p in out["atomic_patterns"]}
        items = []
        for conf in sorted(wanted):
            related = [p for p in out["atomic_patterns"] if p["confirmer"] == conf]
            items.append(
                {
                    "confirmer": conf,
                    "patterns": related,
                    "total_events": sum(p["event_count"] for p in related),
                }
            )
        items.sort(key=lambda x: -x["total_events"])
        return _with_scope_meta(
            {"methodology_version": METHODOLOGY_VERSION, "compare_mode": mode, "items": items, "ai_conclusions": None},
            scope_meta,
        )

    if mode == "combinations":
        return _with_scope_meta(
            {
                "methodology_version": METHODOLOGY_VERSION,
                "compare_mode": mode,
                "items": out["combination_patterns"][:50],
                "ai_conclusions": None,
            },
            scope_meta,
        )

    # lotteries
    by_lot: dict[str, int] = {}
    for p in out["atomic_patterns"]:
        for lid, cnt in (p.get("by_primary_lottery") or {}).items():
            by_lot[lid] = by_lot.get(lid, 0) + int(cnt)
    items = [{"lottery_id": k, "event_count": v} for k, v in sorted(by_lot.items(), key=lambda x: -x[1])]
    return _with_scope_meta(
        {"methodology_version": METHODOLOGY_VERSION, "compare_mode": mode, "items": items, "ai_conclusions": None},
        scope_meta,
    )


# --- J-9 Historial del Número ---


def _audit_nr_query(
    *,
    user: CurrentUser,
    action: str,
    payload: dict[str, Any],
    duration_ms: float | None = None,
) -> None:
    """Auditoría ligera sin secretos (stdout estructurado / logs app)."""
    import logging

    logging.getLogger("lottery.nr.historial").info(
        "nr_historial_query",
        extra={
            "action": action,
            "user_id": str(getattr(user, "id", None) or getattr(user, "sub", None) or ""),
            "payload": payload,
            "duration_ms": duration_ms,
        },
    )


@router.post("/numbers/profile")
async def number_profile(
    body: NumberProfileBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """J-9 — Perfil / expediente resumen del número."""
    import time as _time

    t0 = _time.perf_counter()
    universe, scope, window, _, scope_meta = await _prepare_numbers(db, body)
    svc = NumberExplorerService(universe=universe)
    out = svc.profile(
        number=body.number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        max_horizon=body.max_horizon,
    )
    _audit_nr_query(
        user=user,
        action="numbers.profile",
        payload={
            "number": body.number,
            "date_from": str(body.date_from) if body.date_from else None,
            "date_to": str(body.date_to) if body.date_to else None,
            "trace_id": out.get("trace_id"),
        },
        duration_ms=round((_time.perf_counter() - t0) * 1000, 1),
    )
    out["ai_conclusions"] = None
    return _with_scope_meta(out, scope_meta)


@router.post("/numbers/occurrences")
async def number_occurrences(
    body: NumberOccurrencesBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """J-9 — Apariciones paginadas del número."""
    import time as _time

    t0 = _time.perf_counter()
    universe, scope, window, _, scope_meta = await _prepare_numbers(db, body)
    svc = NumberExplorerService(universe=universe)
    out = svc.occurrences(
        number=body.number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        max_horizon=body.max_horizon,
        page=body.page,
        page_size=body.page_size,
        year=body.year,
        lottery_id=str(body.lottery_id) if body.lottery_id else None,
        condition=body.condition,
        candidate=body.candidate,
        confirmer=body.confirmer,
        order=body.order,
    )
    _audit_nr_query(
        user=user,
        action="numbers.occurrences",
        payload={"number": body.number, "page": body.page, "trace_id": out.get("trace_id")},
        duration_ms=round((_time.perf_counter() - t0) * 1000, 1),
    )
    out["ai_conclusions"] = None
    return _with_scope_meta(out, scope_meta)


@router.post("/numbers/occurrences/detail")
async def number_occurrence_detail(
    body: NumberOccurrenceDetailBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """J-9 — Expediente de una aparición (Modo B)."""
    try:
        primary, confirming, follow_up, scope_meta = await _clamp_scope_ids(db, body.scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    lids = sorted(set(primary) | set(confirming) | set(follow_up))
    try:
        universe, names = await load_universe_from_db(db, lottery_ids=lids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    scope = _scope_from_ids(primary, confirming, follow_up, names)
    window = _window_from_body(body.confirmation_window)
    svc = NumberExplorerService(universe=universe)
    try:
        out = svc.occurrence_detail(
            number=body.number,
            draw_id=body.draw_id,
            scope=scope,
            window=window,
            max_horizon=body.max_horizon,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit_nr_query(
        user=user,
        action="numbers.occurrence_detail",
        payload={"number": body.number, "draw_id": body.draw_id, "trace_id": out.get("trace_id")},
    )
    out["ai_conclusions"] = None
    return _with_scope_meta(out, scope_meta)


@router.post("/numbers/occurrences/next-draws")
async def number_next_draws(
    body: NumberNextDrawsBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """J-9 — Próximos N sorteos (por defecto 7) o días calendario."""
    try:
        lids, _active, scope_meta = await resolve_active_scope_ids(
            db, [str(x) for x in body.follow_up_lottery_ids], require_non_empty=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        universe, _names = await load_universe_from_db(db, lottery_ids=lids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    svc = NumberExplorerService(universe=universe)
    try:
        out = svc.next_draws(
            draw_id=body.draw_id,
            follow_up_lottery_ids=lids,
            count=body.count,
            mode=body.mode,
            tz_name=body.timezone,
            strengthened_candidates=body.strengthened_candidates,
            confirmer_watch=body.confirmer_watch,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit_nr_query(
        user=user,
        action="numbers.next_draws",
        payload={"draw_id": body.draw_id, "mode": body.mode, "count": body.count, "trace_id": out.get("trace_id")},
    )
    out["ai_conclusions"] = None
    return _with_scope_meta(out, scope_meta)


@router.post("/numbers/compare")
async def numbers_compare(
    body: NumbersCompareBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """J-9 — Comparar dos números observados (p. ej. 35 vs 40)."""
    universe, scope, window, _, scope_meta = await _prepare_numbers(db, body)
    svc = NumberExplorerService(universe=universe)
    out = svc.compare_numbers(
        number_a=body.number_a,
        number_b=body.number_b,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        max_horizon=body.max_horizon,
    )
    _audit_nr_query(
        user=user,
        action="numbers.compare",
        payload={"number_a": body.number_a, "number_b": body.number_b, "trace_id": out.get("trace_id")},
    )
    out["ai_conclusions"] = None
    return _with_scope_meta(out, scope_meta)


@router.post("/numbers/why-strengthened")
async def why_strengthened(
    body: WhyStrengthenedBody,
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    __: Annotated[None, require_ai_admin(*_PERMS)],
) -> dict[str, Any]:
    """J-9 — Explicación determinista «¿Por qué se fortaleció?»."""
    universe, scope, window, _, scope_meta = await _prepare_numbers(db, body)
    svc = NumberExplorerService(universe=universe)
    analyzed = None
    if body.draw_id:
        try:
            analyzed = svc.occurrence_detail(
                number=body.number,
                draw_id=body.draw_id,
                scope=scope,
                window=window,
                max_horizon=body.max_horizon,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Historical sample for candidate from profile aggregates (lightweight reuse)
    profile = svc.profile(
        number=body.number,
        scope=scope,
        window=window,
        date_from=body.date_from,
        date_to=body.date_to,
        max_horizon=body.max_horizon,
    )
    cand_hist = {
        int(x["candidato"]): int(x["veces"])
        for x in (profile.get("charts") or {}).get("candidatos_fortalecidos") or []
    }
    r3 = ((profile.get("charts") or {}).get("tasas") or {}).get("response_rate_within_3") or {}
    cycles = (profile.get("charts") or {}).get("ciclos") or {}
    hist = {
        "casos": cand_hist.get(int(body.candidate)),
        "respuesta_3": (
            f"En {r3.get('numerator')} de {r3.get('denominator')} casos evaluables apareció dentro de tres sorteos."
            if r3.get("denominator")
            else None
        ),
        "ciclo": (
            f"Su ciclo típico observado fue de {cycles.get('median')} sorteos."
            if cycles.get("median") is not None
            else None
        ),
    }
    why = svc.why_strengthened(
        number=body.number,
        candidate=body.candidate,
        analyzed=analyzed,
        historical_sample=hist,
    )
    out = {
        "methodology_version": METHODOLOGY_VERSION,
        "trace_id": profile.get("trace_id"),
        "why": why,
        "effective_parameters": {
            "number": body.number,
            "candidate": body.candidate,
            "draw_id": body.draw_id,
        },
        "ai_conclusions": None,
    }
    _audit_nr_query(
        user=user,
        action="numbers.why_strengthened",
        payload={"number": body.number, "candidate": body.candidate, "trace_id": out.get("trace_id")},
    )
    return _with_scope_meta(out, scope_meta)
