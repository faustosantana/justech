"""Tools IA — analizador histórico T1↔T2 (solo resultados calculados)."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.lottery.numeric_relations.historical.aggregates import HistoricalAggregatesService
from app.lottery.numeric_relations.historical.db_universe import load_universe_from_db
from app.lottery.numeric_relations.historical.enums import ConfirmationWindowMode
from app.lottery.numeric_relations.historical.models import (
    ConfirmationWindowConfig,
    LotteryScope,
)
from app.lottery.numeric_relations.historical.service import HistoricalRelationsService
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION
from app.services.lottery_errors import LotteryQueryError


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw)[:10])


async def _resolve_scope(
    resolver: Any,
    params: dict[str, Any],
) -> tuple[LotteryScope, list[str]]:
    primary_names = []
    if params.get("primary_lotteries"):
        primary_names = [str(x) for x in params["primary_lotteries"]]
    elif params.get("lottery"):
        primary_names = [str(params["lottery"])]
    elif params.get("lotteries"):
        primary_names = [str(x) for x in params["lotteries"]]
    if not primary_names:
        raise LotteryQueryError(
            "LOTTERY_REQUIRED",
            "Indica lotería principal (primary). Follow-up por defecto = misma principal.",
        )

    confirming_names = [str(x) for x in (params.get("confirming_lotteries") or primary_names)]
    follow_names = [str(x) for x in (params.get("follow_up_lotteries") or primary_names)]

    names: dict[str, str] = {}
    primary_ids: list[str] = []
    confirming_ids: list[str] = []
    follow_ids: list[str] = []

    async def add(name: str, bucket: list[str]) -> None:
        lot = await resolver.resolve_or_raise(name)
        lid = str(lot.id)
        bucket.append(lid)
        names[lid] = lot.commercial_name or lot.name or name

    for n in primary_names:
        await add(n, primary_ids)
    for n in confirming_names:
        await add(n, confirming_ids)
    for n in follow_names:
        await add(n, follow_ids)

    scope = LotteryScope(
        primary_lottery_ids=tuple(primary_ids),
        confirming_lottery_ids=tuple(confirming_ids),
        follow_up_lottery_ids=tuple(follow_ids),
        lottery_names=names,
    )
    all_ids = sorted(set(primary_ids + confirming_ids + follow_ids))
    return scope, all_ids


def _window(params: dict[str, Any]) -> ConfirmationWindowConfig:
    mode_raw = str(params.get("confirmation_window_mode") or params.get("window_mode") or "SAME_DRAW")
    try:
        mode = ConfirmationWindowMode(mode_raw)
    except ValueError as exc:
        raise LotteryQueryError(
            "WINDOW_INVALID",
            f"confirmation_window_mode inválido: {mode_raw}",
        ) from exc
    return ConfirmationWindowConfig(
        mode=mode,
        timezone=str(params.get("timezone") or "America/Santo_Domingo"),
        hours_after=int(params["hours_after"]) if params.get("hours_after") is not None else None,
        next_k=int(params["next_k"]) if params.get("next_k") is not None else None,
    )


def _observed(params: dict[str, Any]) -> int:
    raw = params.get("observed_number", params.get("number"))
    try:
        n = int(str(raw).lstrip("0") or "0")
    except (TypeError, ValueError) as exc:
        raise LotteryQueryError("NUMBER_INVALID", "observed_number 1..100") from exc
    if n < 1 or n > 100:
        raise LotteryQueryError("NUMBER_INVALID", "observed_number 1..100")
    return n


async def run_historical_tool(
    db: AsyncSession,
    resolver: Any,
    *,
    kind: str,
    params: dict[str, Any],
) -> tuple[Any, int | None, dict[str, Any]]:
    observed = _observed(params)
    scope, all_ids = await _resolve_scope(resolver, params)
    window = _window(params)
    date_from = _parse_date(params.get("date_from") or params.get("from_date"))
    if params.get("year_from") and not date_from:
        date_from = date(int(params["year_from"]), 1, 1)
    if params.get("year") and not date_from:
        date_from = date(int(params["year"]), 1, 1)
    date_to = _parse_date(params.get("date_to") or params.get("to_date"))
    if params.get("year") and not date_to:
        date_to = date(int(params["year"]), 12, 31)

    candidate = int(params["candidate"]) if params.get("candidate") is not None else None
    confirmer = int(params["confirmer"]) if params.get("confirmer") is not None else None
    max_horizon = int(params.get("max_horizon") or 10)

    universe, _names = await load_universe_from_db(
        db,
        lottery_ids=all_ids,
        date_from=date_from,
        date_to=date_to,
    )

    meta = {
        "engine": "lottery.numeric_relations.historical",
        "methodology_version": METHODOLOGY_VERSION,
        "llm_calculates": False,
        "not_probability_of_winning": True,
        "kind": kind,
    }

    if kind == "historical_relation_conditions":
        svc = HistoricalRelationsService(universe=universe)
        payload = svc.search_conditions(
            observed_number=observed,
            scope=scope,
            window=window,
            date_from=date_from,
            date_to=date_to,
            candidate=candidate,
            confirmer=confirmer,
            max_horizon=max_horizon,
        )
        # trim evidence for chat
        payload["atomic_events"] = payload["atomic_events"][:30]
        payload["combination_events"] = payload["combination_events"][:30]
        return payload, payload.get("combination_event_count"), meta

    if kind == "candidate_response_summary":
        svc = HistoricalRelationsService(universe=universe)
        full = svc.search_conditions(
            observed_number=observed,
            scope=scope,
            window=window,
            date_from=date_from,
            date_to=date_to,
            candidate=candidate,
            confirmer=confirmer,
            max_horizon=max_horizon,
        )
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "effective_parameters": full["effective_parameters"],
            "statistics": full["statistics"],
            "candidate_ranking_by_confirmations": full["candidate_ranking_by_confirmations"],
            "disclaimer": "Tasas históricas de respuesta observada; no probabilidad de ganar.",
        }, full.get("combination_event_count"), meta

    if kind in {"confirmer_combinations", "relation_pattern_detail", "compare_historical_patterns"}:
        agg = HistoricalAggregatesService(universe=universe)
        out = agg.compute(
            observed_number=observed,
            scope=scope,
            window=window,
            date_from=date_from,
            date_to=date_to,
            candidate=candidate,
            confirmer=confirmer,
            max_horizon=max_horizon,
        )
        if kind == "confirmer_combinations":
            return {
                "methodology_version": METHODOLOGY_VERSION,
                "combination_patterns": out["combination_patterns"][:40],
                "totals": out["totals"],
                "disclaimer": "Combinaciones calculadas; no certeza futura.",
            }, out["totals"].get("combination_events"), meta
        if kind == "relation_pattern_detail":
            if candidate is None:
                raise LotteryQueryError("CANDIDATE_REQUIRED", "candidate T1 requerido")
            if confirmer is not None:
                patterns = [
                    p
                    for p in out["atomic_patterns"]
                    if p["candidate"] == candidate and p["confirmer"] == confirmer
                ]
            else:
                patterns = [p for p in out["combination_patterns"] if p["candidate"] == candidate][:10]
            return {
                "methodology_version": METHODOLOGY_VERSION,
                "patterns": patterns,
                "matrix_sample": out["matrix"]["cells"][:40],
                "disclaimer": "Detalle de patrón histórico calculado.",
            }, len(patterns), meta
        # compare
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "atomic_patterns": out["atomic_patterns"][:30],
            "combination_patterns": out["combination_patterns"][:30],
            "by_lottery_hint": [
                {"pattern": p["pattern_key"], "by_primary_lottery": p.get("by_primary_lottery")}
                for p in out["atomic_patterns"][:20]
            ],
            "disclaimer": "Comparación histórica; no ranking de apuestas.",
        }, out["totals"].get("atomic_events"), meta

    raise LotteryQueryError("TOOL_ERROR", f"historical kind desconocido: {kind}")
