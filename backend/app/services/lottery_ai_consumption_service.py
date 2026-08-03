"""Lottery IA — consumption / token cost dashboard aggregates (historical DB rows)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotteryAiUsage
from app.models.user import User


def _parse_dt(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            d = date.fromisoformat(raw)
            if end_of_day:
                return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def resolve_period_bounds(
    period: str | None,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[datetime, datetime, str]:
    now = datetime.now(timezone.utc)
    p = (period or "month").strip().lower()
    if p in {"custom", "range", "rango"}:
        start = _parse_dt(date_from) or (now - timedelta(days=30))
        end = _parse_dt(date_to, end_of_day=True) or now
        label = "range"
    elif p in {"today", "hoy", "day"}:
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        end = now
        label = "today"
    elif p in {"week", "semana"}:
        start = now - timedelta(days=7)
        end = now
        label = "week"
    else:
        start = now - timedelta(days=30)
        end = now
        label = "month"
    if end < start:
        start, end = end, start
    return start, end, label


def _provider_family(provider: str | None) -> str:
    p = (provider or "unknown").strip().lower()
    if "openai" in p:
        return "openai"
    if "huawei" in p or "deepseek" in p or "modelarts" in p:
        return "huawei"
    if p in {"local", "local_template"} or p.startswith("local"):
        return "local"
    return p or "unknown"


class LotteryAiConsumptionService:
    def __init__(self, db: AsyncSession, *, tenant_id: UUID | None) -> None:
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(
        self,
        *,
        since: datetime,
        until: datetime,
        user_id: UUID | None = None,
        lottery_key: str | None = None,
    ) -> Select[tuple[LotteryAiUsage]]:
        clauses = [
            LotteryAiUsage.created_at >= since,
            LotteryAiUsage.created_at <= until,
        ]
        if self.tenant_id is not None:
            clauses.append(
                (LotteryAiUsage.tenant_id == self.tenant_id)
                | (LotteryAiUsage.tenant_id.is_(None))
            )
        if user_id is not None:
            clauses.append(LotteryAiUsage.user_id == user_id)
        if lottery_key:
            clauses.append(LotteryAiUsage.lottery_key == lottery_key.strip()[:64])
        return select(LotteryAiUsage).where(and_(*clauses))

    async def dashboard(
        self,
        *,
        period: str | None = "month",
        date_from: str | None = None,
        date_to: str | None = None,
        user_id: UUID | None = None,
        lottery_key: str | None = None,
    ) -> dict[str, Any]:
        since, until, period_label = resolve_period_bounds(
            period, date_from=date_from, date_to=date_to
        )
        rows = (
            await self.db.execute(
                self._base_query(
                    since=since,
                    until=until,
                    user_id=user_id,
                    lottery_key=lottery_key,
                ).order_by(LotteryAiUsage.created_at.asc())
            )
        ).scalars().all()

        by_model: dict[str, dict[str, Any]] = {}
        by_provider: dict[str, dict[str, Any]] = {}
        daily: dict[str, dict[str, float | int]] = {}
        sessions: set[str] = set()
        lotteries: set[str] = set()
        users_seen: set[str] = set()

        total_cost = 0.0
        total_tokens = 0
        total_prompt = 0
        total_completion = 0

        for r in rows:
            model = (r.model or "unknown").strip() or "unknown"
            provider = _provider_family(r.provider)
            key = f"{provider}::{model}"
            prompt = int(r.prompt_tokens or 0)
            completion = int(r.completion_tokens or 0)
            tokens = int(r.total_tokens or (prompt + completion))
            cost = float(r.estimated_cost_usd or 0.0)
            last_use = r.created_at.isoformat() if r.created_at else None

            total_cost += cost
            total_tokens += tokens
            total_prompt += prompt
            total_completion += completion
            if r.session_id:
                sessions.add(str(r.session_id))
            if r.lottery_key:
                lotteries.add(r.lottery_key)
            if r.user_id:
                users_seen.add(str(r.user_id))

            bucket = by_model.setdefault(
                key,
                {
                    "provider": provider,
                    "model": model,
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                    "last_used_at": None,
                },
            )
            bucket["requests"] += 1
            bucket["prompt_tokens"] += prompt
            bucket["completion_tokens"] += completion
            bucket["total_tokens"] += tokens
            bucket["estimated_cost_usd"] = round(float(bucket["estimated_cost_usd"]) + cost, 6)
            if last_use and (
                not bucket["last_used_at"] or last_use > str(bucket["last_used_at"])
            ):
                bucket["last_used_at"] = last_use

            pb = by_provider.setdefault(
                provider,
                {
                    "provider": provider,
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
            )
            pb["requests"] += 1
            pb["prompt_tokens"] += prompt
            pb["completion_tokens"] += completion
            pb["total_tokens"] += tokens
            pb["estimated_cost_usd"] = round(float(pb["estimated_cost_usd"]) + cost, 6)

            day = (r.created_at.astimezone(timezone.utc).date().isoformat() if r.created_at else "")
            if day:
                dbucket = daily.setdefault(
                    day,
                    {
                        "date": day,
                        "requests": 0,
                        "total_tokens": 0,
                        "estimated_cost_usd": 0.0,
                    },
                )
                dbucket["requests"] = int(dbucket["requests"]) + 1
                dbucket["total_tokens"] = int(dbucket["total_tokens"]) + tokens
                dbucket["estimated_cost_usd"] = round(
                    float(dbucket["estimated_cost_usd"]) + cost, 6
                )

        request_n = len(rows)
        model_rows: list[dict[str, Any]] = []
        for bucket in by_model.values():
            req = int(bucket["requests"])
            avg_tokens = round(int(bucket["total_tokens"]) / req, 2) if req else 0.0
            avg_cost = round(float(bucket["estimated_cost_usd"]) / req, 6) if req else 0.0
            share = round((req / request_n) * 100.0, 2) if request_n else 0.0
            model_rows.append(
                {
                    **bucket,
                    "estimated_cost_usd": round(float(bucket["estimated_cost_usd"]), 6),
                    "avg_tokens_per_request": avg_tokens,
                    "avg_cost_per_request": avg_cost,
                    "usage_pct": share,
                }
            )
        model_rows.sort(key=lambda x: (-int(x["requests"]), str(x["provider"]), str(x["model"])))

        provider_rows = sorted(
            (
                {
                    **v,
                    "estimated_cost_usd": round(float(v["estimated_cost_usd"]), 6),
                    "usage_pct": round((int(v["requests"]) / request_n) * 100.0, 2)
                    if request_n
                    else 0.0,
                }
                for v in by_provider.values()
            ),
            key=lambda x: -int(x["requests"]),
        )

        daily_series = [daily[k] for k in sorted(daily.keys())]
        cumulative = 0.0
        cumulative_series: list[dict[str, Any]] = []
        for point in daily_series:
            cumulative = round(cumulative + float(point["estimated_cost_usd"]), 6)
            cumulative_series.append(
                {
                    "date": point["date"],
                    "estimated_cost_usd": float(point["estimated_cost_usd"]),
                    "cumulative_cost_usd": cumulative,
                }
            )

        active = await self._active_model()
        filter_opts = await self._filter_options(since=since, until=until)

        avg_cost_per_lottery = (
            round(total_cost / len(lotteries), 6) if lotteries else None
        )
        avg_cost_per_conversation = (
            round(total_cost / len(sessions), 6) if sessions else None
        )

        return {
            "period": period_label,
            "since": since.isoformat(),
            "until": until.isoformat(),
            "filters": {
                "user_id": str(user_id) if user_id else None,
                "lottery_key": lottery_key,
            },
            "active_model": active,
            "summary": {
                "requests": request_n,
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "total_tokens": total_tokens,
                "estimated_cost_usd": round(total_cost, 6),
                "avg_cost_per_request": round(total_cost / request_n, 6) if request_n else 0.0,
                "avg_tokens_per_request": round(total_tokens / request_n, 2) if request_n else 0.0,
                "unique_conversations": len(sessions),
                "unique_lotteries": len(lotteries),
                "unique_users": len(users_seen),
                "avg_cost_per_lottery": avg_cost_per_lottery,
                "avg_cost_per_conversation": avg_cost_per_conversation,
            },
            "by_model": model_rows,
            "by_provider": provider_rows,
            "charts": {
                "daily": daily_series,
                "by_model": [
                    {
                        "provider": m["provider"],
                        "model": m["model"],
                        "label": f"{m['provider']} / {m['model']}",
                        "requests": m["requests"],
                        "total_tokens": m["total_tokens"],
                        "estimated_cost_usd": m["estimated_cost_usd"],
                        "usage_pct": m["usage_pct"],
                    }
                    for m in model_rows
                ],
                "by_provider": [
                    {
                        "provider": p["provider"],
                        "requests": p["requests"],
                        "total_tokens": p["total_tokens"],
                        "estimated_cost_usd": p["estimated_cost_usd"],
                        "usage_pct": p["usage_pct"],
                    }
                    for p in provider_rows
                ],
                "cumulative_cost": cumulative_series,
            },
            "filter_options": filter_opts,
            "note": (
                "Costos estimados a partir de tarifas por modelo; tokens reales reportados "
                "por el proveedor en cada llamada."
            ),
        }

    async def _active_model(self) -> dict[str, Any]:
        try:
            from app.services.lottery_ai_conversation_settings_service import (
                LotteryAiConversationSettingsService,
            )

            svc = LotteryAiConversationSettingsService(self.db, user_id=None)
            data = await svc.get_or_create_active()
            return {
                "provider": data.get("conversation_provider") or data.get("provider"),
                "model": data.get("conversation_model") or data.get("model"),
                "source": "lottery_ai_settings",
            }
        except Exception:  # noqa: BLE001
            try:
                from app.lottery.ai.conversational_orchestrator.conversation_provider_factory import (
                    get_runtime_settings,
                )

                rt = get_runtime_settings()
                return {
                    "provider": rt.get("conversation_provider"),
                    "model": rt.get("conversation_model"),
                    "source": "runtime_cache",
                }
            except Exception:  # noqa: BLE001
                return {"provider": None, "model": None, "source": "unavailable"}

    async def _filter_options(
        self, *, since: datetime, until: datetime
    ) -> dict[str, Any]:
        q = (
            select(
                LotteryAiUsage.user_id,
                LotteryAiUsage.lottery_key,
            )
            .where(
                LotteryAiUsage.created_at >= since,
                LotteryAiUsage.created_at <= until,
            )
            .distinct()
        )
        if self.tenant_id is not None:
            q = q.where(
                (LotteryAiUsage.tenant_id == self.tenant_id)
                | (LotteryAiUsage.tenant_id.is_(None))
            )
        pairs = (await self.db.execute(q)).all()
        user_ids = sorted({str(uid) for uid, _ in pairs if uid})
        lottery_keys = sorted({str(lk) for _, lk in pairs if lk})

        users: list[dict[str, str]] = []
        if user_ids:
            uid_list = [UUID(x) for x in user_ids]
            urows = (
                await self.db.execute(select(User).where(User.id.in_(uid_list)))
            ).scalars().all()
            by_id = {str(u.id): u for u in urows}
            for uid in user_ids:
                u = by_id.get(uid)
                label = getattr(u, "email", None) or getattr(u, "full_name", None) or uid
                users.append({"id": uid, "label": str(label)})

        return {
            "users": users,
            "lotteries": [{"key": k, "label": k} for k in lottery_keys],
        }
