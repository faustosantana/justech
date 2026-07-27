"""Ejecutor tipado de tools Lotería IA — sin SQL libre, con permisos y auditoría."""

from __future__ import annotations

import time
import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_permissions import role_has_permission
from app.models.lottery import LotteryAuditLog, LotterySavedQuery
from app.services.lottery_ai_contracts import TOOL_PERMISSIONS, LotteryToolName
from app.services.lottery_aliases import LotteryResolver, describe_alias_resolution
from app.services.lottery_exceptions import LotteryQueryError
from app.services.lottery_query_service import LotteryQueryService
from app.services.lottery_service import LotteryService


class ToolExecutionResult(BaseModel):
    tool: str
    status: str  # success | error | forbidden
    duration_ms: int
    data: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    result_count: int | None = None
    structured_type: str = "lottery_result"
    summary_for_context: dict[str, Any] = Field(default_factory=dict)


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    if isinstance(obj, (date,)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    return obj


class LotteryToolExecutor:
    def __init__(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str | None,
        is_superadmin: bool = False,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role
        self.is_superadmin = is_superadmin
        self.query = LotteryQueryService(db)
        self.catalog = LotteryService(db)
        self.resolver = LotteryResolver(db)

    def _allowed(self, tool: LotteryToolName) -> bool:
        if self.is_superadmin:
            return True
        perms = TOOL_PERMISSIONS.get(tool, ())
        return any(role_has_permission(self.role, p) for p in perms)

    async def _audit(
        self,
        *,
        tool: str,
        parameters: dict[str, Any],
        result_count: int | None,
        duration_ms: int,
        error: str | None,
    ) -> None:
        row = LotteryAuditLog(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action="tool_invoke",
            tool_name=tool,
            parameters=_serialize(parameters) if parameters else {},
            result_count=result_count,
            duration_ms=duration_ms,
            error=error,
        )
        self.db.add(row)
        await self.db.flush()

    async def execute(
        self,
        tool: LotteryToolName,
        params: dict[str, Any],
        *,
        structured_type: str = "lottery_result",
        session_context: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        t0 = time.perf_counter()
        if not self._allowed(tool):
            ms = int((time.perf_counter() - t0) * 1000)
            await self._audit(
                tool=tool.value,
                parameters=params,
                result_count=0,
                duration_ms=ms,
                error="FORBIDDEN",
            )
            return ToolExecutionResult(
                tool=tool.value,
                status="forbidden",
                duration_ms=ms,
                error_code="FORBIDDEN",
                error_message=f"Permiso insuficiente para {tool.value}",
                structured_type="lottery_error",
            )

        try:
            data, count, ctx_summary = await self._dispatch(tool, params, session_context or {})
            ms = int((time.perf_counter() - t0) * 1000)
            await self._audit(
                tool=tool.value,
                parameters=params,
                result_count=count,
                duration_ms=ms,
                error=None,
            )
            return ToolExecutionResult(
                tool=tool.value,
                status="success",
                duration_ms=ms,
                data=_serialize(data),
                result_count=count,
                structured_type=structured_type,
                summary_for_context=ctx_summary,
            )
        except LotteryQueryError as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            await self._audit(
                tool=tool.value,
                parameters=params,
                result_count=0,
                duration_ms=ms,
                error=exc.code,
            )
            st = "lottery_ambiguity" if "AMBIGUOUS" in exc.code or "PENDING" in exc.code else "lottery_error"
            if exc.code == "NO_RESULTS":
                st = "lottery_no_results"
            return ToolExecutionResult(
                tool=tool.value,
                status="error",
                duration_ms=ms,
                error_code=exc.code,
                error_message=exc.message,
                structured_type=st,
                data={"candidates": getattr(exc, "details", None) or {}},
            )
        except Exception as exc:  # noqa: BLE001 — surface as controlled tool error
            ms = int((time.perf_counter() - t0) * 1000)
            await self._audit(
                tool=tool.value,
                parameters=params,
                result_count=0,
                duration_ms=ms,
                error=type(exc).__name__,
            )
            return ToolExecutionResult(
                tool=tool.value,
                status="error",
                duration_ms=ms,
                error_code="TOOL_ERROR",
                error_message="No se pudo completar la consulta estructurada.",
                structured_type="lottery_error",
            )

    async def _dispatch(
        self,
        tool: LotteryToolName,
        params: dict[str, Any],
        session_context: dict[str, Any],
    ) -> tuple[Any, int | None, dict[str, Any]]:
        if tool == LotteryToolName.LIST_LOTTERIES:
            res = await self.catalog.list_lotteries(
                limit=int(params.get("limit", 100)),
                ai_only=True,
                include_aggregates=False,
            )
            return res, res.total, {}

        if tool == LotteryToolName.RESOLVE_LOTTERY:
            q = str(params.get("lottery") or params.get("q") or "")
            return describe_alias_resolution(q), 1, {}

        if tool == LotteryToolName.GET_RESULT_BY_DATE:
            res = await self.query.by_date(
                params["lottery"],
                params["date"] if isinstance(params["date"], date) else date.fromisoformat(str(params["date"])),
                game=params.get("game"),
            )
            nums: list[str] = []
            ref = None
            for d in res.draws:
                ref = d.source_reference or ref
                nums.extend(n.number_raw for n in d.numbers)
            return res, res.total, {"source_reference": ref, "numbers": nums, "semantics": "by_date"}

        if tool == LotteryToolName.GET_FOLLOWING_DAYS:
            res = await self.query.following_days(
                params["lottery"],
                params["date"] if isinstance(params["date"], date) else date.fromisoformat(str(params["date"])),
                int(params.get("days", 7)),
                include_base_date=bool(params.get("include_base_date", False)),
                game=params.get("game"),
            )
            return (
                res,
                res.total_draws,
                {
                    "semantics": "calendar_days",
                    "calendar_from": res.calendar_from,
                    "calendar_to": res.calendar_to,
                },
            )

        if tool == LotteryToolName.GET_FOLLOWING_DRAWS:
            res = await self.query.following_draws(
                params["lottery"],
                params["date"] if isinstance(params["date"], date) else date.fromisoformat(str(params["date"])),
                int(params.get("count", 7)),
                include_base_date=bool(params.get("include_base_date", False)),
                game=params.get("game"),
            )
            return res, res.total, {"semantics": "next_n_draws"}

        if tool == LotteryToolName.GET_PREVIOUS_DAYS:
            res = await self.query.previous_days(
                params["lottery"],
                params["date"] if isinstance(params["date"], date) else date.fromisoformat(str(params["date"])),
                int(params.get("days", 7)),
                include_base_date=bool(params.get("include_base_date", False)),
                game=params.get("game"),
            )
            return (
                res,
                res.total_draws,
                {
                    "semantics": "calendar_days",
                    "calendar_from": res.calendar_from,
                    "calendar_to": res.calendar_to,
                },
            )

        if tool == LotteryToolName.GET_PREVIOUS_DRAWS:
            res = await self.query.previous_draws(
                params["lottery"],
                params["date"] if isinstance(params["date"], date) else date.fromisoformat(str(params["date"])),
                int(params.get("count", 7)),
                include_base_date=bool(params.get("include_base_date", False)),
                game=params.get("game"),
            )
            return res, res.total, {"semantics": "previous_n_draws"}

        if tool == LotteryToolName.GET_RESULTS_RANGE:
            res = await self.query.range(
                params["lottery"],
                params["from_date"] if isinstance(params["from_date"], date) else date.fromisoformat(str(params["from_date"])),
                params["to_date"] if isinstance(params["to_date"], date) else date.fromisoformat(str(params["to_date"])),
                game=params.get("game"),
                number=params.get("number"),
                position=params.get("position"),
                page=int(params.get("page", 1)),
                page_size=int(params.get("page_size", 50)),
            )
            return res, res.pagination.total, {"semantics": "range"}

        if tool == LotteryToolName.GET_NUMBER_OCCURRENCES:
            res = await self.query.by_number(
                params["lottery"],
                str(params["number"]),
                from_date=params.get("from_date"),
                to_date=params.get("to_date"),
                position=params.get("position"),
                number_type=params.get("number_type"),
                page=int(params.get("page", 1)),
                page_size=int(params.get("page_size", 50)),
            )
            return res, res.pagination.total, {"numbers": [str(params["number"])]}

        if tool == LotteryToolName.CALCULATE_FREQUENCIES:
            res = await self.query.frequencies(
                params["lottery"],
                params["from_date"] if isinstance(params["from_date"], date) else date.fromisoformat(str(params["from_date"])),
                params["to_date"] if isinstance(params["to_date"], date) else date.fromisoformat(str(params["to_date"])),
                position=params.get("position"),
                number_type=params.get("number_type"),
                limit=int(params.get("limit", 20)),
            )
            return res, len(res.items), {}

        if tool == LotteryToolName.FIND_REPETITIONS:
            res = await self.query.repetitions(
                params["lottery"],
                params["from_date"] if isinstance(params["from_date"], date) else date.fromisoformat(str(params["from_date"])),
                params["to_date"] if isinstance(params["to_date"], date) else date.fromisoformat(str(params["to_date"])),
                min_count=int(params.get("min_count", 2)),
                position=params.get("position"),
                number_type=params.get("number_type"),
            )
            return res, len(res.items), {
                "calendar_from": res.from_date,
                "calendar_to": res.to_date,
                "numbers": [i.number for i in res.items[:10]],
            }

        if tool == LotteryToolName.FIND_NEXT_OCCURRENCES:
            after = params.get("after_date") or params.get("date")
            res = await self.query.next_occurrences(
                params["lottery"],
                str(params["number"]),
                after if isinstance(after, date) else date.fromisoformat(str(after)),
                limit=int(params.get("limit", 10)),
                position=params.get("position"),
            )
            return res, len(res.items), {"numbers": [str(params["number"])]}

        if tool == LotteryToolName.COMPARE_LOTTERIES:
            if params.get("number"):
                number = str(params["number"])
                items = []
                for lot_name in list(params["lotteries"]):
                    res = await self.query.by_number(
                        lot_name,
                        number,
                        from_date=params.get("from_date"),
                        to_date=params.get("to_date"),
                        page=1,
                        page_size=5,
                    )
                    last = None
                    rows = getattr(res, "items", None) or []
                    if rows:
                        first = rows[0]
                        last = getattr(first, "draw_date", None) or (
                            first.get("draw_date") if isinstance(first, dict) else None
                        )
                    total = getattr(getattr(res, "pagination", None), "total", None)
                    if total is None:
                        total = getattr(res, "total", len(rows))
                    items.append(
                        {
                            "lottery": lot_name,
                            "number": number,
                            "occurrences": total,
                            "last_draw_date": str(last) if last else None,
                        }
                    )
                return {
                    "mode": "number_compare",
                    "number": number,
                    "items": items,
                    "disclaimer": "Análisis histórico informativo; no es predicción.",
                }, sum(i["occurrences"] or 0 for i in items), {
                    "semantics": "compare:number",
                    "numbers": [number],
                }
            res = await self.query.compare(
                list(params["lotteries"]),
                params["from_date"] if isinstance(params["from_date"], date) else date.fromisoformat(str(params["from_date"])),
                params["to_date"] if isinstance(params["to_date"], date) else date.fromisoformat(str(params["to_date"])),
                params.get("mode", "repeated_numbers"),
                position=params.get("position"),
                number_type=params.get("number_type"),
                include_draws=bool(params.get("include_draws", False)),
                limit=int(params.get("limit", 50)),
                intersection_scope=params.get("intersection_scope", "within_range"),
            )
            return res, None, {"semantics": f"compare:{params.get('mode', 'repeated_numbers')}"}

        if tool == LotteryToolName.CROSS_LOTTERY_ANALYSIS:
            res = await self.query.cross_lottery(
                list(params["lotteries"]),
                params["from_date"] if isinstance(params["from_date"], date) else date.fromisoformat(str(params["from_date"])),
                params["to_date"] if isinstance(params["to_date"], date) else date.fromisoformat(str(params["to_date"])),
                params.get("mode", "within_range"),
                number=params.get("number"),
            )
            return res, None, {"semantics": f"cross:{params.get('mode', 'within_range')}"}

        if tool == LotteryToolName.GET_COVERAGE:
            health = await self.catalog.health()
            return health, health.draws_count, {}

        if tool == LotteryToolName.SAVE_QUERY:
            name = str(params.get("name") or "Consulta")[:255]
            payload = {
                "context": session_context,
                "last_operation": session_context.get("last_operation"),
                "last_lottery": session_context.get("last_lottery"),
                "base_date": session_context.get("base_date"),
                "last_from_date": session_context.get("last_from_date"),
                "last_to_date": session_context.get("last_to_date"),
            }
            row = LotterySavedQuery(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                name=name,
                payload=payload,
            )
            self.db.add(row)
            await self.db.flush()
            return {"id": str(row.id), "name": name, "payload": payload}, 1, {"saved_query_id": str(row.id)}

        if tool == LotteryToolName.GET_SAVED_QUERIES:
            q = await self.db.execute(
                select(LotterySavedQuery)
                .where(
                    LotterySavedQuery.tenant_id == self.tenant_id,
                    LotterySavedQuery.user_id == self.user_id,
                )
                .order_by(LotterySavedQuery.updated_at.desc())
                .limit(50)
            )
            rows = q.scalars().all()
            items = [{"id": str(r.id), "name": r.name, "payload": r.payload} for r in rows]
            return {"items": items, "total": len(items)}, len(items), {}

        if tool == LotteryToolName.GET_LATEST_RESULTS:
            from app.services.lottery_admin_service import LotteryAdminService

            dash = await LotteryAdminService(self.db).dashboard_v2(
                tenant_id=self.tenant_id, user_id=self.user_id
            )
            return {"items": dash.latest_results}, len(dash.latest_results), {}

        if tool == LotteryToolName.GET_DRAW_COUNT:
            health = await self.catalog.health()
            lot = None
            if params.get("lottery"):
                lot = await self.resolver.resolve_or_raise(str(params["lottery"]))
            data = {
                "lotteries_count": health.lotteries_count,
                "draws_count": health.draws_count,
            }
            if lot:
                data["lottery"] = lot.name
                data["lottery_draw_count"] = lot.draw_count
                data["first_draw_date"] = lot.first_draw_date
                data["last_draw_date"] = lot.last_draw_date
            return data, health.draws_count, {}

        if tool in (LotteryToolName.GET_TOP_NUMBERS, LotteryToolName.GET_BOTTOM_NUMBERS):
            from_d = params.get("from_date") or params.get("from")
            to_d = params.get("to_date") or params.get("to")
            if not from_d or not to_d:
                raise LotteryQueryError("DATE_REQUIRED", "Se requieren from_date y to_date")
            from_date = from_d if isinstance(from_d, date) else date.fromisoformat(str(from_d))
            to_date = to_d if isinstance(to_d, date) else date.fromisoformat(str(to_d))
            lottery = str(params.get("lottery") or "")
            res = await self.query.frequencies(
                lottery,
                from_date,
                to_date,
                limit=int(params.get("limit", 10)),
            )
            items = list(getattr(res, "items", None) or getattr(res, "frequencies", None) or [])
            if tool == LotteryToolName.GET_BOTTOM_NUMBERS:
                items = list(reversed(items))
            return {"items": _serialize(items[: int(params.get("limit", 10))])}, len(items), {
                "semantics": "frequencies"
            }

        if tool == LotteryToolName.GET_LAST_OCCURRENCE:
            lottery = str(params["lottery"])
            number = str(params["number"])
            pos_filter = params.get("position")
            if pos_filter is not None:
                try:
                    pos_filter = int(pos_filter)
                except (TypeError, ValueError):
                    pos_filter = None
            # DESC: page=1 must be the most recent occurrence (not the oldest).
            res = await self.query.by_number(
                lottery,
                number,
                page=1,
                page_size=1,
                order="desc",
                position=pos_filter,
            )
            last_date = None
            position = None
            items = list(getattr(res, "items", None) or getattr(res, "occurrences", None) or [])
            if items:
                first = items[0]
                last_date = getattr(first, "draw_date", None) or (
                    first.get("draw_date") if isinstance(first, dict) else None
                )
                position = getattr(first, "position_label", None) or getattr(first, "position", None)
                if isinstance(first, dict):
                    position = first.get("position_label") or first.get("position")
            iso = None
            if last_date is not None:
                iso = last_date.isoformat() if hasattr(last_date, "isoformat") else str(last_date)[:10]
            return res, getattr(res, "total", 1), {
                "semantics": "last_occurrence",
                "last_occurrence_date": iso,
                "base_date": iso,
                "lottery": lottery,
                "number": number,
                "position": position,
            }

        if tool == LotteryToolName.GET_INTERVAL_STATISTICS:
            lottery = str(params["lottery"])
            number = str(params["number"])
            res = await self.query.by_number(lottery, number, page=1, page_size=100)
            # Derive intervals from occurrence dates if present
            dates: list[date] = []
            for item in getattr(res, "items", []) or getattr(res, "occurrences", []) or []:
                d = getattr(item, "draw_date", None) or (item.get("draw_date") if isinstance(item, dict) else None)
                if d:
                    dates.append(d if isinstance(d, date) else date.fromisoformat(str(d)))
            dates = sorted(set(dates))
            gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
            avg = (sum(gaps) / len(gaps)) if gaps else None
            return {
                "lottery": lottery,
                "number": number,
                "occurrences": len(dates),
                "first": dates[0].isoformat() if dates else None,
                "last": dates[-1].isoformat() if dates else None,
                "avg_gap_days": avg,
                "min_gap_days": min(gaps) if gaps else None,
                "max_gap_days": max(gaps) if gaps else None,
                "disclaimer": "Análisis histórico informativo; no es predicción.",
            }, len(dates), {"semantics": "interval_statistics"}

        if tool == LotteryToolName.GET_SYNC_STATUS:
            from app.config import settings as cfg

            rows = (
                await self.catalog.list_lotteries(limit=200, include_aggregates=False)
            ).items
            sync_on = [r for r in rows if getattr(r, "is_sync_enabled", False)]
            return {
                "global_sync_enabled": bool(cfg.lottery_sync_enabled),
                "global_write_enabled": bool(cfg.lottery_sync_write_enabled),
                "global_auto_write_enabled": bool(cfg.lottery_sync_automatic_write_enabled),
                "scheduler_enabled": bool(cfg.lottery_scheduler_enabled),
                "scheduler_mode": cfg.lottery_scheduler_mode,
                "worker_standalone": bool(cfg.lottery_sync_worker_standalone),
                "lotteries_sync_enabled": len(sync_on),
                "sync_lotteries": [
                    {"name": r.name, "source_id": r.source_id, "last_draw_date": str(getattr(r, "last_draw_date", None))}
                    for r in sync_on
                ],
            }, len(sync_on), {}

        if tool == LotteryToolName.GET_DATA_QUALITY:
            from app.lottery.analytics import LotteryAnalyticsEngine
            from uuid import UUID as _UUID

            q = str(params.get("lottery") or session_context.get("lottery") or "")
            lot = await self.resolver.resolve_or_raise(q)
            data = await LotteryAnalyticsEngine(self.db).data_quality(_UUID(str(lot.id)))
            return data, 1, {"confidence": "high", "limitations": ["descriptivo"]}

        if tool == LotteryToolName.GET_ANOMALIES:
            from app.lottery.analytics import LotteryAnalyticsEngine
            from uuid import UUID as _UUID

            q = str(params.get("lottery") or session_context.get("lottery") or "")
            lot = await self.resolver.resolve_or_raise(q)
            data = await LotteryAnalyticsEngine(self.db).anomalies(_UUID(str(lot.id)))
            return data, data.get("count", 0), {}

        if tool == LotteryToolName.GET_SOURCE_HEALTH:
            from app.models.lottery import LotterySource
            from sqlalchemy import select

            rows = (await self.db.execute(select(LotterySource).limit(100))).scalars().all()
            items = [
                {
                    "source_key": r.source_key,
                    "role": r.role,
                    "health_status": r.health_status,
                    "circuit_state": r.circuit_state,
                    "latency_ema_ms": r.latency_ema_ms,
                    "enabled": r.enabled,
                }
                for r in rows
            ]
            return {"sources": items, "count": len(items)}, len(items), {}

        if tool == LotteryToolName.GET_SYNC_WINDOWS:
            from app.lottery.sync.dispatcher import dispatch_status

            data = await dispatch_status(self.db)
            return data, len(data.get("sync_enabled_due") or []), {}

        if tool == LotteryToolName.GET_HOT_COLD:
            from app.lottery.analytics import LotteryAnalyticsEngine
            from uuid import UUID as _UUID

            q = str(params.get("lottery") or session_context.get("lottery") or "Leidsa")
            focus = str(params.get("focus") or "both")
            window = int(params.get("window_draws") or 30)
            lot = await self.resolver.resolve_or_raise(q)
            data = await LotteryAnalyticsEngine(self.db).hot_cold(
                _UUID(str(lot.id)),
                window_draws=window,
                focus=focus,
            )
            data["lottery"] = lot.commercial_name or lot.name
            return data, len(data.get("hot") or data.get("cold") or data.get("cold_by_frequency") or [1]), {
                "disclaimer": data.get("definition"),
                "metric_used": data.get("metric_used"),
                "window_draws": data.get("window_draws"),
            }

        if tool == LotteryToolName.GET_COINCIDENCES:
            from app.lottery.analytics import LotteryAnalyticsEngine
            from uuid import UUID as _UUID
            from datetime import date as date_cls

            ids = params.get("lottery_ids") or []
            if not ids and session_context.get("lottery_ids"):
                ids = session_context["lottery_ids"]
            if len(ids) < 2:
                # fallback: resolve compare list from names
                raise LotteryQueryError("VALIDATION", "Se requieren al menos 2 loterías para coincidencias")
            on_date = params.get("on_date")
            od = date_cls.fromisoformat(on_date) if on_date else None
            data = await LotteryAnalyticsEngine(self.db).coincidences(
                [_UUID(str(x)) for x in ids], on_date=od
            )
            return data, len(data.get("matches") or []), {}

        if tool == LotteryToolName.GET_MISSING_TODAY:
            from app.lottery.core.timeutil import local_today
            from app.models.lottery import LotteryDraw, LotteryLottery
            from sqlalchemy import func, select

            today = local_today()
            lots = (
                await self.db.execute(
                    select(LotteryLottery).where(LotteryLottery.is_sync_enabled.is_(True))
                )
            ).scalars().all()
            missing = []
            for lot in lots:
                cnt = int(
                    (
                        await self.db.execute(
                            select(func.count())
                            .select_from(LotteryDraw)
                            .where(LotteryDraw.lottery_id == lot.id, LotteryDraw.draw_date == today)
                        )
                    ).scalar_one()
                )
                if cnt == 0:
                    missing.append(
                        {
                            "name": lot.commercial_name or lot.name,
                            "source_id": lot.source_id,
                            "last_draw_date": lot.last_draw_date.isoformat() if lot.last_draw_date else None,
                        }
                    )
            return {
                "local_today": today.isoformat(),
                "missing": missing,
                "count": len(missing),
                "explanation": (
                    "Resultados Hoy = 0 cuando no hay draws con draw_date = hoy en la zona "
                    "America/Santo_Domingo, o cuando el sync aún no validó el sorteo del día."
                ),
            }, len(missing), {}

        if tool == LotteryToolName.COMPARE_NUMBER_PERIODS:
            return await self._compare_number_periods(params)

        if tool == LotteryToolName.COMPARE_NUMBER_ACROSS_LOTTERIES:
            number = str(params["number"])
            lots = [str(x) for x in (params.get("lotteries") or [])][:8]
            if not lots:
                raise LotteryQueryError("VALIDATION", "Se requieren loterías")
            rows = []
            for lot in lots:
                try:
                    res = await self.query.by_number(lot, number, page=1, page_size=1, order="desc")
                    items = getattr(res, "occurrences", None) or []
                    last = None
                    pos = None
                    if items:
                        last = items[0].draw_date
                        pos = items[0].position_label or items[0].position
                    total = getattr(getattr(res, "pagination", None), "total", None) or getattr(res, "total", 0)
                    rows.append(
                        {
                            "lottery": lot,
                            "number": number,
                            "occurrences": total,
                            "last_date": last.isoformat() if last else None,
                            "position": pos,
                            "found": bool(last),
                        }
                    )
                except Exception:  # noqa: BLE001 — partial ok
                    rows.append(
                        {
                            "lottery": lot,
                            "number": number,
                            "occurrences": 0,
                            "last_date": None,
                            "found": False,
                            "error": "sin_datos",
                        }
                    )
            rows_sorted = sorted(rows, key=lambda r: r.get("last_date") or "", reverse=True)
            return {
                "number": number,
                "rows": rows_sorted,
                "metric": "last_occurrence_and_count_across_lotteries",
                "limitations": ["Máximo 8 loterías por turno", "Análisis histórico, no predicción"],
            }, len(rows_sorted), {"semantics": "compare_across_lotteries"}

        if tool == LotteryToolName.GET_POSITION_DISTRIBUTION:
            from app.lottery.analytics import LotteryAnalyticsEngine
            from datetime import timedelta
            from uuid import UUID as _UUID

            lot = await self.resolver.resolve_or_raise(str(params["lottery"]))
            window = int(params.get("window_draws") or 100)
            to_d = date.today()
            from_d = to_d - timedelta(days=max(window, 30))
            data = await LotteryAnalyticsEngine(self.db).position_distribution(
                _UUID(str(lot.id)), from_date=from_d, to_date=to_d
            )
            data["lottery"] = lot.commercial_name or lot.name
            data["from"] = from_d.isoformat()
            data["to"] = to_d.isoformat()
            data["window_draws_hint"] = window
            data["metric"] = "position_distribution"
            data["limitations"] = ["Distribución descriptiva en la ventana de fechas aproximada"]
            return data, 1, {}

        if tool == LotteryToolName.GET_OVERDUE_NUMBERS:
            # Dedicated overdue = hot_cold cold_interval
            params = {**params, "focus": "cold_interval"}
            return await self._dispatch(LotteryToolName.GET_HOT_COLD, params, session_context)

        if tool == LotteryToolName.GET_MONTHLY_TREND:
            return await self._monthly_trend(params)

        if tool == LotteryToolName.GET_YEARLY_COMPARISON:
            # Alias to compare current calendar year vs previous for a number (or top freqs)
            if params.get("number"):
                return await self._compare_number_periods(
                    {
                        **params,
                        "period_a": "current_year",
                        "period_b": "previous_year",
                    }
                )
            raise LotteryQueryError("VALIDATION", "Indica el número a comparar entre años")

        if tool == LotteryToolName.GET_LOTTERY_SUMMARY:
            lot = await self.resolver.resolve_or_raise(str(params["lottery"]))
            return {
                "lottery": lot.commercial_name or lot.name,
                "source_id": lot.source_id,
                "draw_count": lot.draw_count,
                "first_draw_date": lot.first_draw_date.isoformat() if lot.first_draw_date else None,
                "last_draw_date": lot.last_draw_date.isoformat() if lot.last_draw_date else None,
                "sync_enabled": bool(getattr(lot, "is_sync_enabled", False)),
                "auto_write_enabled": bool(getattr(lot, "is_auto_write_enabled", False)),
                "metric": "lottery_summary",
                "limitations": ["Resumen operativo; no es predicción"],
            }, 1, {"semantics": "lottery_summary"}

        if tool == LotteryToolName.GET_DATA_COMPLETENESS:
            from app.lottery.analytics import LotteryAnalyticsEngine
            from uuid import UUID as _UUID

            if params.get("lottery"):
                lot = await self.resolver.resolve_or_raise(str(params["lottery"]))
                data = await LotteryAnalyticsEngine(self.db).data_quality(_UUID(str(lot.id)))
                data["lottery"] = lot.commercial_name or lot.name
            else:
                health = await self.catalog.health()
                data = {
                    "lotteries_count": health.lotteries_count,
                    "draws_count": health.draws_count,
                    "metric": "global_completeness_proxy",
                }
            data["metric"] = data.get("metric") or "data_completeness"
            data["limitations"] = ["Completitud descriptiva sobre draws almacenados"]
            return data, 1, {}

        if tool == LotteryToolName.GET_EXPECTED_VS_RECEIVED:
            # Today: expected = sync-enabled lotteries; received = those with draw today
            miss, n, _ = await self._dispatch(LotteryToolName.GET_MISSING_TODAY, {}, session_context)
            sync_on = int(miss.get("count") or 0)
            # Reconstruct expected count
            from app.models.lottery import LotteryLottery
            from sqlalchemy import select, func

            expected = int(
                (
                    await self.db.execute(
                        select(func.count()).select_from(LotteryLottery).where(
                            LotteryLottery.is_sync_enabled.is_(True)
                        )
                    )
                ).scalar_one()
            )
            received = max(0, expected - sync_on)
            return {
                "local_today": miss.get("local_today"),
                "expected_sync_enabled": expected,
                "received_today": received,
                "pending": sync_on,
                "missing": miss.get("missing") or [],
                "metric": "expected_vs_received_today",
                "definition": "Esperado = loterías con sync habilitado; recibido = draw_date=hoy",
                "limitations": ["No modela calendarios de sorteo futuros; solo día local actual"],
                "explanation": miss.get("explanation"),
            }, expected, {}

        if tool == LotteryToolName.GET_LATEST_AVAILABLE_DATE:
            if params.get("lottery"):
                lot = await self.resolver.resolve_or_raise(str(params["lottery"]))
                return {
                    "lottery": lot.commercial_name or lot.name,
                    "last_draw_date": lot.last_draw_date.isoformat() if lot.last_draw_date else None,
                    "draw_count": lot.draw_count,
                    "metric": "latest_available_date",
                }, 1, {}
            rows = (await self.catalog.list_lotteries(limit=100, include_aggregates=False)).items
            items = [
                {
                    "lottery": r.commercial_name or r.name,
                    "last_draw_date": str(getattr(r, "last_draw_date", None) or ""),
                    "sync_enabled": bool(getattr(r, "is_sync_enabled", False)),
                }
                for r in rows
            ]
            items.sort(key=lambda x: x.get("last_draw_date") or "", reverse=True)
            return {
                "items": items[:20],
                "most_recent": items[0] if items else None,
                "metric": "latest_available_date_catalog",
            }, len(items), {}

        if tool == LotteryToolName.EXPLAIN_ANALYSIS_METHOD:
            metric = str(params.get("metric") or "general")
            defs = {
                "hot": "Caliente = mayor frecuencia relativa en la muestra de N sorteos.",
                "cold_frequency": "Frío por frecuencia = menor frecuencia relativa en la muestra.",
                "cold_interval": "Atrasado = más días desde la última aparición (intervalo).",
                "frequency": "Frecuencia histórica = apariciones / sorteos en el período; no es probabilidad futura.",
                "general": (
                    "Lottery IA usa tools tipadas sobre PostgreSQL. "
                    "Reporta muestra, período, métrica y limitaciones. "
                    "No predice resultados ni recomienda apuestas."
                ),
            }
            return {
                "metric": metric,
                "definition": defs.get(metric, defs["general"]),
                "definitions": defs,
                "limitations": ["Explicación metodológica; no implica predicción"],
            }, 1, {"semantics": "explain_method"}

        if tool == LotteryToolName.ANALYZE_NUMERIC_RELATIONS:
            return await self._analyze_numeric_relations(params)

        if tool == LotteryToolName.RUN_COMPLETE_ANALYSIS:
            return await self._run_complete_analysis(params)

        if tool in {
            LotteryToolName.HISTORICAL_RELATION_CONDITIONS,
            LotteryToolName.CANDIDATE_RESPONSE_SUMMARY,
            LotteryToolName.CONFIRMER_COMBINATIONS,
            LotteryToolName.RELATION_PATTERN_DETAIL,
            LotteryToolName.COMPARE_HISTORICAL_PATTERNS,
        }:
            from app.lottery.numeric_relations.historical.tools_bridge import run_historical_tool

            kind_map = {
                LotteryToolName.HISTORICAL_RELATION_CONDITIONS: "historical_relation_conditions",
                LotteryToolName.CANDIDATE_RESPONSE_SUMMARY: "candidate_response_summary",
                LotteryToolName.CONFIRMER_COMBINATIONS: "confirmer_combinations",
                LotteryToolName.RELATION_PATTERN_DETAIL: "relation_pattern_detail",
                LotteryToolName.COMPARE_HISTORICAL_PATTERNS: "compare_historical_patterns",
            }
            return await run_historical_tool(
                self.db,
                self.resolver,
                kind=kind_map[tool],
                params=params,
            )

        raise LotteryQueryError("TOOL_ERROR", f"Tool no implementada: {tool.value}")

    async def _analyze_numeric_relations(
        self, params: dict[str, Any]
    ) -> tuple[Any, int | None, dict[str, Any]]:
        """Fachada única: DB history → NumericRelationsService (sin recalcular en el tool)."""
        from app.lottery.numeric_relations.db_history import analyze_from_db
        from app.lottery.numeric_relations.models import OccurrenceLimit
        from app.services.lottery_prediction_service import PredictionMotorService

        # Gate: motor ACTIVO only (Control Center Predicciones)
        try:
            motor_svc = PredictionMotorService(self.db)
            if not await motor_svc.is_executable("numeric_relations"):
                raise LotteryQueryError(
                    "MOTOR_INACTIVE",
                    "El motor Relaciones Numéricas está inactivo o no ejecutable. "
                    "Actívelo en Lottery IA → Predicciones.",
                )
        except LotteryQueryError:
            raise
        except Exception:
            # Si el registry aún no está migrado, no bloquear el motor v1.0.0.
            pass

        raw_n = params.get("observed_number", params.get("number"))
        try:
            observed = int(str(raw_n).lstrip("0") or "0")
        except (TypeError, ValueError) as exc:
            raise LotteryQueryError(
                "NUMBER_INVALID", "observed_number debe ser un entero 1..100"
            ) from exc
        if observed < 1 or observed > 100:
            raise LotteryQueryError(
                "NUMBER_INVALID", "observed_number debe estar entre 1 y 100"
            )

        lot_names: list[str] = []
        if params.get("lotteries"):
            lot_names = [str(x) for x in params["lotteries"] if x]
        elif params.get("lottery"):
            lot_names = [str(params["lottery"])]
        if not lot_names:
            raise LotteryQueryError(
                "LOTTERY_REQUIRED",
                "Indica al menos una lotería (no se inventan loterías)",
            )

        mode = str(params.get("occurrence_mode") or "").strip().lower()
        if mode in {"all", "all_occurrences"}:
            limit = OccurrenceLimit.all()
        elif mode == "last_k":
            k_raw = params.get("occurrence_k", params.get("k"))
            if k_raw is None:
                raise LotteryQueryError(
                    "OCCURRENCE_LIMIT_REQUIRED",
                    "occurrence_k es obligatorio cuando occurrence_mode=last_k",
                )
            limit = OccurrenceLimit.last_k(int(k_raw))
        else:
            raise LotteryQueryError(
                "OCCURRENCE_LIMIT_REQUIRED",
                "Indica occurrence_mode=last_k (con k=5|10|20) o all; no hay default oculto",
            )

        lottery_ids = []
        name_by_id: dict[str, str] = {}
        for name in lot_names:
            lot = await self.resolver.resolve_or_raise(name)
            lottery_ids.append(lot.id)
            name_by_id[str(lot.id)] = lot.commercial_name or lot.name or name

        result = await analyze_from_db(
            self.db,
            observed_number=observed,
            lottery_ids=lottery_ids,
            limit=limit,
            lottery_names=name_by_id,
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
        engine_meta = dict(payload.get("analysis_metadata") or {})
        payload["metadata"] = {
            "engine": "lottery.numeric_relations",
            "llm_calculates": False,
            "huawei_invents": False,
            "exclude_observed_from_matches": True,
            "disclaimer": (
                "Señal histórica del método de relaciones numéricas; "
                "no es certeza ni garantía de resultados futuros."
            ),
            **engine_meta,
        }
        ranking = payload.get("ranking") or []
        return (
            payload,
            len(ranking),
            {
                "semantics": "numeric_relations_analysis",
                "observed_number": observed,
                "occurrences_used": payload.get("occurrences_used"),
                "top_companion": ranking[0].get("number") if ranking else None,
                "top_score": ranking[0].get("score") if ranking else None,
                "draw_ids_analyzed_count": engine_meta.get("draw_ids_analyzed_count"),
                "possible_content_duplicate_draws_detected": engine_meta.get(
                    "possible_content_duplicate_draws_detected"
                ),
            },
        )

    async def _run_complete_analysis(
        self, params: dict[str, Any]
    ) -> tuple[Any, int | None, dict[str, Any]]:
        """Complete Analysis Engine + historical evidence (explanatory layer)."""
        from app.lottery.numeric_relations.active_scope import get_active_analysis_lotteries
        from app.lottery.numeric_relations.analysis_engine.complete_analysis_service import (
            run_complete_analysis,
        )
        from app.lottery.numeric_relations.analysis_engine.historical_relation_evidence import (
            flat_rows_from_draw_refs,
        )
        from app.lottery.numeric_relations.historical.db_universe import load_universe_from_db

        raw_n = params.get("observed_number", params.get("number"))
        try:
            observed = int(str(raw_n).lstrip("0") or "0")
        except (TypeError, ValueError) as exc:
            raise LotteryQueryError(
                "NUMBER_INVALID", "El número debe estar entre 1 y 100"
            ) from exc
        if observed < 1 or observed > 100:
            raise LotteryQueryError("NUMBER_INVALID", "El número debe estar entre 1 y 100")

        confirmer = params.get("confirmer") or params.get("same_day_confirmer")
        confirmer_i = None
        if confirmer is not None:
            try:
                confirmer_i = int(str(confirmer).lstrip("0") or "0")
            except (TypeError, ValueError):
                confirmer_i = None
            if confirmer_i is not None and not (1 <= confirmer_i <= 100):
                confirmer_i = None

        draw_date = params.get("date") or params.get("analysis_date")
        date_s = str(draw_date)[:10] if draw_date else None
        lottery_hint = params.get("lottery")
        # If the user did not pass a date, resolve last occurrence so same-day
        # confirmation can run (without asking for a form field).
        if not date_s:
            try:
                from app.services.lottery_query_service import LotteryQueryService
                from app.services.lottery_result_service import LotteryResultService

                q = LotteryQueryService(self.db)
                lots_try: list[str] = []
                if lottery_hint:
                    lots_try = [str(lottery_hint)]
                else:
                    # Prefer featured/sync product lotteries so same-day context
                    # matches the Analizar board (not obscure catalog entries).
                    try:
                        featured = await LotteryResultService(self.db).list_featured_lotteries()
                        lots_try = [str(x.get("name")) for x in (featured or []) if x.get("name")]
                    except Exception:
                        lots_try = []
                    if not lots_try:
                        active = await get_active_analysis_lotteries(self.db)
                        # Prefer known product names first
                        preferred = (
                            "Lotería Nacional",
                            "Nacional Noche",
                            "Leidsa",
                            "Loteka",
                            "Quiniela Loteka",
                            "Quiniela Leidsa",
                        )
                        by_name = {x.name: x.name for x in active}
                        lots_try = [n for n in preferred if n in by_name]
                        if not lots_try:
                            lots_try = [x.name for x in active[:8]]
                best = None
                preferred = (
                    "Lotería Nacional",
                    "Nacional Noche",
                    "Leidsa",
                    "Loteka",
                    "Quiniela Loteka",
                    "Quiniela Leidsa",
                    "Real",
                    "La Primera",
                )
                # Prefer product order, but among preferred hits choose the most recent date.
                # This recovers validated cases like 35 @ Nacional 2026-06-23 even when
                # other featured lotteries also contain the number.
                import unicodedata

                def _norm(s: str) -> str:
                    raw = unicodedata.normalize("NFKD", str(s or ""))
                    return "".join(ch for ch in raw if not unicodedata.combining(ch)).strip().lower()

                lots_norm = {_norm(x): x for x in lots_try}
                ordered: list[str] = []
                seen_lots: set[str] = set()
                for n in preferred:
                    hit = lots_norm.get(_norm(n))
                    if not hit:
                        # soft contains match (e.g. "nacional")
                        key = _norm(n).split()[-1]
                        for ln, orig in lots_norm.items():
                            if key and key in ln and orig not in seen_lots:
                                hit = orig
                                break
                    if hit and hit not in seen_lots:
                        ordered.append(hit)
                        seen_lots.add(hit)
                for n in lots_try:
                    if n not in seen_lots:
                        ordered.append(n)
                        seen_lots.add(n)
                candidates: list[tuple[str, str]] = []
                for lot_name in ordered:
                    if not lot_name:
                        continue
                    try:
                        res = await q.by_number(
                            str(lot_name),
                            str(observed).zfill(2),
                            page=1,
                            page_size=12,
                            order="desc",
                        )
                        items = getattr(res, "items", None) or getattr(res, "occurrences", None) or []
                        if not items:
                            res = await q.by_number(
                                str(lot_name),
                                str(observed),
                                page=1,
                                page_size=12,
                                order="desc",
                            )
                            items = getattr(res, "items", None) or getattr(res, "occurrences", None) or []
                        for first in items:
                            d = getattr(first, "draw_date", None) or (
                                first.get("draw_date") if isinstance(first, dict) else None
                            )
                            if not d:
                                continue
                            candidates.append((str(d)[:10], str(lot_name)))
                    except Exception:
                        continue
                # Also harvest recent featured calendar days containing the number
                try:
                    from datetime import date as date_cls
                    from datetime import timedelta

                    svc_scan = LotteryResultService(self.db)
                    today = date_cls.today()
                    for delta in range(0, 90):
                        day = today - timedelta(days=delta)
                        rows = await svc_scan.get_by_date(day, featured_only=True)
                        if not rows:
                            continue
                        for row in rows:
                            if not isinstance(row, dict):
                                continue
                            lot_name = str(row.get("lottery") or row.get("lottery_name") or "")
                            vals = []
                            for key in ("primera", "first", "n1", "numbers"):
                                val = row.get(key)
                                if val is None:
                                    continue
                                if isinstance(val, (list, tuple)):
                                    vals.extend(val)
                                else:
                                    vals.append(val)
                            for n in vals:
                                try:
                                    if int(str(n).lstrip("0") or "0") == int(observed):
                                        candidates.append((day.isoformat(), lot_name or "featured"))
                                        break
                                except Exception:
                                    pass
                except Exception:
                    pass
                if candidates:
                    # Prefer a day with same-day T1×T2 confirmation when available.
                    from datetime import date as date_cls

                    from app.lottery.numeric_relations.catalog import build_catalog
                    from app.lottery.numeric_relations.analysis_engine.same_day_context import (
                        build_same_day_context,
                        find_same_day_cross_confirmations,
                    )

                    cat = build_catalog()
                    svc_res = LotteryResultService(self.db)
                    confirmed: list[tuple[str, str]] = []
                    uniq_dates = sorted({c[0] for c in candidates}, reverse=True)[:15]
                    for iso in uniq_dates:
                        try:
                            rows = await svc_res.get_by_date(
                                date_cls.fromisoformat(iso),
                                featured_only=True,
                            )
                            if not rows:
                                continue
                            ctx_day = build_same_day_context(
                                rows,
                                draw_date=iso,
                                positions=["first"],
                                exclude_numbers=[observed],
                            )
                            crosses = find_same_day_cross_confirmations(
                                seed_numbers=[observed],
                                confirmer_numbers=list(ctx_day.confirmer_numbers or []),
                                catalog=cat,
                                day_context=ctx_day,
                                date_s=iso,
                            )
                            if crosses:
                                lot = next((l for d, l in candidates if d == iso), candidates[0][1])
                                confirmed.append((iso, lot))
                        except Exception:
                            continue
                    if confirmed:
                        best = max(confirmed, key=lambda x: x[0])
                    else:
                        def _rank(item: tuple[str, str]) -> tuple[int, str]:
                            name = _norm(item[1])
                            prio = 0
                            if "nacional" in name:
                                prio = 3
                            elif "leidsa" in name:
                                prio = 2
                            elif "loteka" in name:
                                prio = 1
                            return (prio, item[0])

                        best = max(candidates, key=_rank)
                if best:
                    date_s = best[0]
                    if not lottery_hint:
                        lottery_hint = best[1]
            except Exception:
                pass

        # If confirmer provided without date, locate a featured day containing both.
        if confirmer_i and not date_s:
            try:
                from datetime import date as date_cls
                from datetime import timedelta

                from app.lottery.numeric_relations.catalog import build_catalog
                from app.lottery.numeric_relations.analysis_engine.same_day_context import (
                    build_same_day_context,
                    find_same_day_cross_confirmations,
                )
                from app.services.lottery_result_service import LotteryResultService

                svc_res = LotteryResultService(self.db)
                cat = build_catalog()
                today = date_cls.today()
                fallback_day = None
                for delta in range(0, 180):
                    day = today - timedelta(days=delta)
                    rows = await svc_res.get_by_date(day, featured_only=True)
                    if not rows:
                        continue
                    ctx_day = build_same_day_context(
                        rows,
                        draw_date=day.isoformat(),
                        positions=["first"],
                        exclude_numbers=[],
                    )
                    nums = {int(x) for x in (ctx_day.confirmer_numbers or [])}
                    for a in ctx_day.appearances or []:
                        try:
                            nums.add(int(a.number))
                        except Exception:
                            pass
                    if observed not in nums or confirmer_i not in nums:
                        continue
                    if fallback_day is None:
                        fallback_day = day.isoformat()
                    crosses = find_same_day_cross_confirmations(
                        seed_numbers=[observed],
                        confirmer_numbers=[confirmer_i],
                        catalog=cat,
                        day_context=ctx_day,
                        date_s=day.isoformat(),
                    )
                    if crosses:
                        date_s = day.isoformat()
                        break
                if not date_s:
                    date_s = fallback_day
            except Exception:
                pass

        period = str(params.get("historical_period") or "all")
        include_hist = bool(params.get("include_historical", True))

        hist_rows: list[dict[str, Any]] = []
        if include_hist:
            try:
                lots = await get_active_analysis_lotteries(self.db)
                ids = [x.id for x in lots]
                if ids:
                    universe, _ = await load_universe_from_db(
                        self.db,
                        lottery_ids=ids,
                        date_from=None,
                        date_to=None,
                        max_draws=80000,
                    )
                    hist_rows = flat_rows_from_draw_refs(list(universe._all))
            except Exception:
                hist_rows = []

        payload_req: dict[str, Any] = {
            "numbers": [observed],
            "same_day_confirmers": [confirmer_i] if confirmer_i else [],
            "mode": "socio",
            "derivation_depth": 0,
            "create_signals": False,
            "explanation_level": "analitico",
            "date": date_s,
            "historical_period": period,
            "include_historical": include_hist,
        }
        if hist_rows:
            payload_req["historical_draws"] = hist_rows

        if date_s:
            try:
                from datetime import date as date_cls

                from app.lottery.numeric_relations.analysis_engine.same_day_context import (
                    build_same_day_context,
                )
                from app.services.lottery_result_service import LotteryResultService

                rows = await LotteryResultService(self.db).get_by_date(
                    date_cls.fromisoformat(date_s), featured_only=True
                )
                ctx = build_same_day_context(
                    rows,
                    draw_date=date_s,
                    positions=["first"],
                    exclude_numbers=[observed],
                )
                payload_req["same_day_context"] = ctx.to_dict()
                merged = list(payload_req.get("same_day_confirmers") or [])
                seen = {observed}
                for n in merged + list(ctx.confirmer_numbers):
                    v = int(n)
                    if v in seen:
                        continue
                    seen.add(v)
                    merged.append(v)
                payload_req["same_day_confirmers"] = merged
            except Exception:
                pass

        result = run_complete_analysis(payload_req, persist=False)
        data = result.to_dict()
        primary = data.get("primary_signal") or {}
        hist = data.get("historical_evidence") or {}
        narr = (data.get("explanation") or {}) if isinstance(data.get("explanation"), dict) else {}
        hist_narr = hist.get("narrative") or {}
        metrics = hist.get("metrics") or {}

        user_facing = {
            "type": "lottery_complete_analysis",
            "observed_number": observed,
            "confirmer": confirmer_i,
            "date": date_s,
            "lottery": lottery_hint or params.get("lottery"),
            "primary": {
                "number": primary.get("number"),
                "reason": primary.get("reason")
                or hist_narr.get("conclusion")
                or narr.get("summary"),
            },
            "alternatives": [
                {"number": a.get("number")}
                for a in (data.get("alternatives") or [])[:6]
                if a.get("number") is not None
            ],
            "table1_sources": primary.get("table1_sources") or [],
            "table2_confirmers": primary.get("table2_confirmers") or [],
            "same_day_cross": [
                {
                    "origen": c.get("observed_x"),
                    "companero": c.get("companion_c"),
                    "confirmador": c.get("confirmer_y"),
                    "loteria_origen": c.get("lottery_x"),
                    "loteria_confirmador": c.get("lottery_y"),
                }
                for c in (data.get("same_day_cross") or [])[:8]
            ],
            "historical": {
                "periodo": hist.get("period_label"),
                "casos_equivalentes": metrics.get("exact_cases"),
                "aciertos_exactos": metrics.get("exact_hits"),
                "familia_tabla_1": metrics.get("t1_family_hits"),
                "vecinos_tabla_2": metrics.get("t2_neighbor_hits"),
                "d1": metrics.get("d1_hits"),
                "d3": metrics.get("d3_hits"),
                "d7": metrics.get("d7_hits"),
                "resumen": hist_narr.get("historical_behavior")
                or metrics.get("evidence_quantity_message"),
            },
            "comparison": hist.get("comparison") or hist_narr.get("comparison"),
            "conclusion": hist_narr.get("conclusion") or narr.get("conclusion") or narr.get("summary"),
            "warning": hist_narr.get("warning")
            or "El histórico describe comportamientos anteriores y no garantiza repetición.",
            "disclaimer": (
                "Análisis estructural del motor determinístico. "
                "No es predicción ni recomendación de apuestas."
            ),
        }
        # Follow-up: compare primary vs rival without inventing engine scores.
        rival = params.get("compare_with")
        follow = params.get("follow_up")
        if rival is not None:
            try:
                rival_i = int(str(rival).lstrip("0") or "0")
            except (TypeError, ValueError):
                rival_i = None
            primary_n = (user_facing.get("primary") or {}).get("number")
            if rival_i and primary_n is not None and int(rival_i) != int(primary_n):
                alts = {int(a.get("number")) for a in user_facing.get("alternatives") or [] if a.get("number") is not None}
                t1 = user_facing.get("table1_sources") or []
                t2 = user_facing.get("table2_confirmers") or []
                same = user_facing.get("same_day_cross") or []
                why_primary = []
                if t1:
                    why_primary.append("tiene respaldo de Tabla 1")
                if t2 or same:
                    why_primary.append("tiene confirmación de Tabla 2 / cruce del mismo día")
                why_primary.append("es el candidato principal del motor")
                rival_bits = []
                if rival_i in alts:
                    rival_bits.append("aparece solo como alternativa")
                else:
                    rival_bits.append("no es el candidato principal")
                if not t1:
                    rival_bits.append("sin el mismo peso de Tabla 1 que el principal")
                user_facing["rival_comparison"] = {
                    "primary": int(primary_n),
                    "rival": rival_i,
                    "texto": (
                        f"El {primary_n} supera al {rival_i} porque "
                        + ", ".join(why_primary)
                        + f". El {rival_i} "
                        + " y ".join(rival_bits)
                        + "."
                    ),
                }
                if follow == "compare_rival":
                    user_facing["conclusion"] = user_facing["rival_comparison"]["texto"]
        if follow == "historical" and (user_facing.get("historical") or {}).get("resumen"):
            user_facing["conclusion"] = user_facing["historical"]["resumen"]

        return (
            user_facing,
            1 if primary.get("number") is not None else 0,
            {
                "semantics": "complete_analysis",
                "observed_number": observed,
                "primary": primary.get("number"),
                "exact_historical_cases": metrics.get("exact_cases"),
                "exact_hits": metrics.get("exact_hits"),
            },
        )


    async def _compare_number_periods(self, params: dict[str, Any]) -> tuple[Any, int | None, dict[str, Any]]:
        from datetime import timedelta

        lottery = str(params["lottery"])
        number = str(params["number"])
        today = date.today()
        period_a = str(params.get("period_a") or "current_year")
        period_b = str(params.get("period_b") or "previous_year")

        def _bounds(key: str) -> tuple[date, date, str]:
            if key == "current_year":
                return date(today.year, 1, 1), today, f"año {today.year}"
            if key == "previous_year":
                y = today.year - 1
                return date(y, 1, 1), date(y, 12, 31), f"año {y}"
            if key.startswith("last_"):
                n = int(key.split("_", 1)[1])
                return today - timedelta(days=n), today, f"últimos {n} días"
            # ISO ranges "YYYY-MM-DD:YYYY-MM-DD"
            if ":" in key:
                a, b = key.split(":", 1)
                return date.fromisoformat(a), date.fromisoformat(b), f"{a}→{b}"
            return date(today.year, 1, 1), today, period_a

        a0, a1, a_label = _bounds(period_a)
        b0, b1, b_label = _bounds(period_b)

        async def _period_stats(from_d: date, to_d: date) -> dict[str, Any]:
            res = await self.query.by_number(
                lottery, number, from_date=from_d, to_date=to_d, page=1, page_size=1, order="desc"
            )
            occ = getattr(getattr(res, "pagination", None), "total", None) or getattr(res, "total", 0) or 0
            # Approximate draws in period via frequencies total or range query
            try:
                rng = await self.query.range(
                    lottery, from_d, to_d, page=1, page_size=1
                )
                draws = getattr(getattr(rng, "pagination", None), "total", None) or getattr(rng, "total", 0) or 0
            except Exception:  # noqa: BLE001
                draws = 0
            rel = (float(occ) / float(draws) * 100.0) if draws else None
            return {
                "from": from_d.isoformat(),
                "to": to_d.isoformat(),
                "occurrences": int(occ),
                "draws": int(draws),
                "relative_frequency_pct": round(rel, 3) if rel is not None else None,
            }

        stats_a = await _period_stats(a0, a1)
        stats_b = await _period_stats(b0, b1)
        delta_occ = stats_a["occurrences"] - stats_b["occurrences"]
        delta_rel = None
        if stats_a["relative_frequency_pct"] is not None and stats_b["relative_frequency_pct"] is not None:
            delta_rel = round(stats_a["relative_frequency_pct"] - stats_b["relative_frequency_pct"], 3)

        more = "igual"
        if stats_a["relative_frequency_pct"] is not None and stats_b["relative_frequency_pct"] is not None:
            if stats_a["relative_frequency_pct"] > stats_b["relative_frequency_pct"]:
                more = "period_a"
            elif stats_a["relative_frequency_pct"] < stats_b["relative_frequency_pct"]:
                more = "period_b"
        elif stats_a["occurrences"] > stats_b["occurrences"]:
            more = "period_a"
        elif stats_a["occurrences"] < stats_b["occurrences"]:
            more = "period_b"

        return {
            "lottery": lottery,
            "number": number,
            "period_a": {"label": a_label, **stats_a},
            "period_b": {"label": b_label, **stats_b},
            "delta_occurrences": delta_occ,
            "delta_relative_frequency_pct": delta_rel,
            "higher_relative_frequency": more,
            "metric": "compare_number_periods_relative_frequency",
            "definition": (
                "Frecuencia relativa = apariciones del número / sorteos del período. "
                "Es estadística histórica, no probabilidad de que salga."
            ),
            "limitations": [
                "Períodos con distinta cantidad de sorteos se comparan por frecuencia relativa",
                "No implica predicción",
            ],
        }, 2, {"semantics": "compare_number_periods"}

    async def _monthly_trend(self, params: dict[str, Any]) -> tuple[Any, int | None, dict[str, Any]]:
        from datetime import timedelta

        from app.models.lottery import LotteryDraw, LotteryDrawNumber
        from sqlalchemy import func, select

        lot = await self.resolver.resolve_or_raise(str(params["lottery"]))
        months = int(params.get("months") or 12)
        to_d = date.today()
        from_d = to_d - timedelta(days=max(30, months * 31))
        number = params.get("number")
        q = (
            select(
                func.date_trunc("month", LotteryDraw.draw_date).label("m"),
                func.count().label("cnt"),
            )
            .select_from(LotteryDraw)
            .where(
                LotteryDraw.lottery_id == lot.id,
                LotteryDraw.draw_date >= from_d,
                LotteryDraw.draw_date <= to_d,
            )
            .group_by("m")
            .order_by("m")
        )
        if number:
            num = str(number).zfill(2) if len(str(number)) <= 2 else str(number)
            q = (
                select(
                    func.date_trunc("month", LotteryDraw.draw_date).label("m"),
                    func.count().label("cnt"),
                )
                .select_from(LotteryDrawNumber)
                .join(LotteryDraw, LotteryDraw.id == LotteryDrawNumber.draw_id)
                .where(
                    LotteryDraw.lottery_id == lot.id,
                    LotteryDrawNumber.number_value == num,
                    LotteryDraw.draw_date >= from_d,
                    LotteryDraw.draw_date <= to_d,
                )
                .group_by("m")
                .order_by("m")
            )
        rows = (await self.db.execute(q)).all()
        series = [
            {
                "month": (r[0].date().isoformat() if hasattr(r[0], "date") else str(r[0])[:10]),
                "count": int(r[1]),
            }
            for r in rows
        ]
        return {
            "lottery": lot.commercial_name or lot.name,
            "number": number,
            "from": from_d.isoformat(),
            "to": to_d.isoformat(),
            "series": series,
            "metric": "monthly_trend",
            "limitations": ["Agregación mensual descriptiva"],
        }, len(series), {}
