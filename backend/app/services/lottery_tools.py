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
            res = await self.query.by_number(lottery, number, page=1, page_size=1)
            return res, getattr(res, "total", 1), {"semantics": "last_occurrence"}

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

        raise LotteryQueryError("TOOL_ERROR", f"Tool no implementada: {tool.value}")
