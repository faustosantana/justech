"""LotteryResultService — unique facade for official draw results.

The Motor and J-11A must use this service; never query lottery_draws tables directly.
Reuses LotteryRepository + LotteryQueryService + LotterySyncRun. No second scraper.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.lottery import LotteryDraw, LotteryLottery, LotterySyncRun
from app.services.lottery_query_service import LotteryQueryService
from app.services.lottery_repository import LotteryRepository
def _num_map(draw: LotteryDraw) -> dict[int, str]:
    out: dict[int, str] = {}
    for n in draw.numbers or []:
        if (n.number_type or "principal") not in {"principal", "quiniela", ""}:
            continue
        out[int(n.position)] = n.number_value
    return out


def flatten_draw(draw: LotteryDraw, lottery: LotteryLottery) -> dict[str, Any]:
    nums = _num_map(draw)
    return {
        "draw_id": str(draw.id),
        "lottery_id": str(lottery.id),
        "lottery": lottery.name,
        "lottery_slug": lottery.slug,
        "country": lottery.country_code or lottery.country,
        "date": draw.draw_date.isoformat() if draw.draw_date else None,
        "primera": nums.get(1),
        "segunda": nums.get(2),
        "tercera": nums.get(3),
        "hora": draw.draw_time.isoformat() if draw.draw_time else None,
        "game_name": draw.game_name,
        "estado": "ok",
        "origen": draw.source_reference or "official_db",
        "source_url": draw.source_url,
        "scraped_at": draw.scraped_at.isoformat() if draw.scraped_at else None,
    }


class LotteryResultService:
    """Central read/sync-status API over official lottery tables."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LotteryRepository(db)
        self.query = LotteryQueryService(db)

    async def inventory(self) -> dict[str, Any]:
        draws = int(await self.db.scalar(select(func.count()).select_from(LotteryDraw)) or 0)
        lotteries = int(await self.db.scalar(select(func.count()).select_from(LotteryLottery)) or 0)
        featured = int(
            await self.db.scalar(
                select(func.count())
                .select_from(LotteryLottery)
                .where(LotteryLottery.is_featured.is_(True))
            )
            or 0
        )
        last = await self.db.scalar(select(func.max(LotteryDraw.draw_date)))
        return {
            "database": settings.lottery_sync_allowed_database,
            "schema": "jaios",
            "tables": ["lottery_lotteries", "lottery_draws", "lottery_draw_numbers"],
            "draws_count": draws,
            "lotteries_count": lotteries,
            "featured_lotteries_count": featured,
            "last_draw_date": last.isoformat() if last else None,
            "production_modified": False,
        }

    async def list_featured_lotteries(self) -> list[dict[str, Any]]:
        q = await self.db.execute(
            select(LotteryLottery)
            .where(LotteryLottery.is_featured.is_(True))
            .order_by(LotteryLottery.name)
        )
        return [
            {
                "id": str(l.id),
                "name": l.name,
                "slug": l.slug,
                "country": l.country_code or l.country,
                "is_sync_enabled": l.is_sync_enabled,
                "is_auto_write_enabled": getattr(l, "is_auto_write_enabled", None),
                "last_draw_date": l.last_draw_date.isoformat() if l.last_draw_date else None,
            }
            for l in q.scalars().all()
        ]

    async def _lottery_by_slug_or_id(self, lottery: str) -> LotteryLottery | None:
        try:
            return await self.query.resolver.resolve_or_raise(lottery)
        except Exception:
            return None

    async def get_by_date(
        self,
        draw_date: date,
        *,
        lottery: str | None = None,
        featured_only: bool = True,
        country: str | None = None,
        number: str | None = None,
    ) -> list[dict[str, Any]]:
        lots = await self._lotteries(lottery=lottery, featured_only=featured_only, country=country)
        rows: list[dict[str, Any]] = []
        for lot in lots:
            draws = await self.repo.draws_by_date(lot.id, draw_date)
            for d in draws:
                flat = flatten_draw(d, lot)
                if number and number not in {
                    flat.get("primera"),
                    flat.get("segunda"),
                    flat.get("tercera"),
                }:
                    continue
                rows.append(flat)
        return rows

    async def get_latest_n_dates(
        self, n: int = 7, *, featured_only: bool = True
    ) -> list[dict[str, Any]]:
        n = max(1, min(n, 90))
        last = await self.db.scalar(select(func.max(LotteryDraw.draw_date)))
        if not last:
            return []
        from_d = last - timedelta(days=n - 1)
        return await self.get_range(from_d, last, featured_only=featured_only)

    async def get_by_lottery(
        self,
        lottery: str,
        *,
        limit: int = 50,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[dict[str, Any]]:
        lot = await self._lottery_by_slug_or_id(lottery)
        if not lot:
            return []
        to_d = to_date or date.today()
        from_d = from_date or (to_d - timedelta(days=30))
        draws, _ = await self.repo.draws_in_range(
            lot.id, from_d, to_d, sort="desc", limit=limit, offset=0
        )
        return [flatten_draw(d, lot) for d in draws]

    async def get_range(
        self,
        from_date: date,
        to_date: date,
        *,
        lottery: str | None = None,
        featured_only: bool = True,
        country: str | None = None,
        number: str | None = None,
        limit_per_lottery: int = 200,
    ) -> list[dict[str, Any]]:
        lots = await self._lotteries(lottery=lottery, featured_only=featured_only, country=country)
        rows: list[dict[str, Any]] = []
        for lot in lots:
            draws, _ = await self.repo.draws_in_range(
                lot.id,
                from_date,
                to_date,
                number=number,
                sort="desc",
                limit=limit_per_lottery,
                offset=0,
            )
            rows.extend(flatten_draw(d, lot) for d in draws)
        rows.sort(key=lambda r: (r.get("date") or "", r.get("lottery") or ""), reverse=True)
        return rows

    async def get_history(
        self,
        lottery: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        lot = await self._lottery_by_slug_or_id(lottery)
        if not lot:
            return {"lottery": lottery, "total": 0, "items": []}
        to_d = date.today()
        from_d = date(2000, 1, 1)
        offset = max(0, (page - 1) * page_size)
        draws, total = await self.repo.draws_in_range(
            lot.id, from_d, to_d, sort="desc", limit=page_size, offset=offset
        )
        return {
            "lottery": lot.slug,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [flatten_draw(d, lot) for d in draws],
        }

    async def get_pending(
        self, draw_date: date | None = None, *, featured_only: bool = True
    ) -> dict[str, Any]:
        """Featured lotteries missing draws for the given date (default: yesterday)."""
        target = draw_date or (date.today() - timedelta(days=1))
        lots = await self._lotteries(featured_only=featured_only)
        missing: list[dict[str, Any]] = []
        present: list[str] = []
        for lot in lots:
            draws = await self.repo.draws_by_date(lot.id, target)
            if draws:
                present.append(lot.slug)
            else:
                missing.append({"slug": lot.slug, "name": lot.name, "date": target.isoformat()})
        return {
            "date": target.isoformat(),
            "present": present,
            "missing": missing,
            "pending_count": len(missing),
        }

    async def sync_status(self) -> dict[str, Any]:
        inv = await self.inventory()
        last_run = (
            await self.db.execute(
                select(LotterySyncRun).order_by(LotterySyncRun.started_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        last_ok = (
            await self.db.execute(
                select(LotterySyncRun)
                .where(LotterySyncRun.status.in_(("ok", "success", "completed")))
                .order_by(LotterySyncRun.completed_at.desc().nullslast())
                .limit(1)
            )
        ).scalar_one_or_none()

        interval = max(1, int(settings.lottery_sync_interval_minutes))
        next_update = None
        if settings.lottery_scheduler_enabled and last_run and last_run.started_at:
            next_update = (last_run.started_at + timedelta(minutes=interval)).isoformat()

        run_summary = None
        if last_run:
            duration = None
            if last_run.started_at and last_run.completed_at:
                duration = (last_run.completed_at - last_run.started_at).total_seconds()
            run_summary = {
                "id": str(last_run.id),
                "status": last_run.status,
                "source": last_run.source,
                "dry_run": last_run.dry_run,
                "write_enabled": last_run.write_enabled,
                "records_fetched": last_run.records_fetched,
                "records_new": last_run.records_new,
                "records_inserted": last_run.records_inserted,
                "records_unchanged": last_run.records_unchanged,
                "records_updated": last_run.records_updated,
                "errors": last_run.errors,
                "error_message": last_run.error_message,
                "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
                "completed_at": last_run.completed_at.isoformat() if last_run.completed_at else None,
                "duration_seconds": duration,
            }

        return {
            **inv,
            "last_update": (
                last_ok.completed_at.isoformat()
                if last_ok and last_ok.completed_at
                else (last_run.completed_at.isoformat() if last_run and last_run.completed_at else None)
            ),
            "next_update": next_update,
            "scheduler_enabled": settings.lottery_scheduler_enabled,
            "scheduler_mode": settings.lottery_scheduler_mode,
            "sync_enabled": settings.lottery_sync_enabled,
            "sync_write_enabled": settings.lottery_sync_write_enabled,
            "automatic_write_enabled": settings.lottery_sync_automatic_write_enabled,
            "state": self._state_label(last_run),
            "last_run": run_summary,
            "reused_components": [
                "ElBoletoApiAdapter",
                "LotterySyncWriter",
                "LotterySchedulerService",
                "LotteryRepository",
                "LotteryQueryService",
            ],
            "second_scraper_created": False,
            "production_modified": False,
        }

    def _state_label(self, last_run: LotterySyncRun | None) -> str:
        if not settings.lottery_scheduler_enabled:
            return "SCHEDULER_DISABLED"
        if (settings.lottery_scheduler_mode or "").lower() == "disabled":
            return "MODE_DISABLED"
        if last_run is None:
            return "NO_RUNS"
        if last_run.errors or (last_run.status or "").lower() in {"error", "failed"}:
            return "ERROR"
        if last_run.dry_run:
            return "OBSERVE_DRY_RUN"
        if last_run.write_enabled:
            return "WRITE_OK" if (last_run.status or "").lower() in {"ok", "success", "completed"} else last_run.status
        return last_run.status or "UNKNOWN"

    async def _lotteries(
        self,
        *,
        lottery: str | None = None,
        featured_only: bool = True,
        country: str | None = None,
    ) -> list[LotteryLottery]:
        if lottery:
            lot = await self._lottery_by_slug_or_id(lottery)
            return [lot] if lot else []
        q = select(LotteryLottery)
        if featured_only:
            q = q.where(LotteryLottery.is_featured.is_(True))
        if country:
            q = q.where(
                (LotteryLottery.country_code == country) | (LotteryLottery.country == country)
            )
        q = q.order_by(LotteryLottery.name)
        return list((await self.db.execute(q)).scalars().all())


def get_results_status_sync() -> dict[str, Any]:
    """Sync helper for J-11A (no event-loop required)."""

    async def _run() -> dict[str, Any]:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            return await LotteryResultService(db).sync_status()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # nested — return degraded snapshot from settings only
            return {
                "degraded": True,
                "scheduler_enabled": settings.lottery_scheduler_enabled,
                "scheduler_mode": settings.lottery_scheduler_mode,
                "message": "DB async loop busy; use /lottery/resultados/sync-status",
                "production_modified": False,
            }
        return loop.run_until_complete(_run())
    except RuntimeError:
        return asyncio.run(_run())
    except Exception as e:
        return {
            "error": str(e),
            "scheduler_enabled": settings.lottery_scheduler_enabled,
            "production_modified": False,
        }
