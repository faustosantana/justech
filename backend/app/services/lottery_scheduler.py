"""APScheduler worker for lottery staging automation (pattern mirrors dgcp_scheduler)."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_shutting_down = False


async def _lottery_scheduler_tick() -> None:
    if _shutting_down:
        return
    if not settings.lottery_scheduler_enabled:
        return
    mode = (settings.lottery_scheduler_mode or "disabled").lower()
    if mode == "disabled":
        return

    from app.db.session import AsyncSessionLocal
    from app.services.lottery_scheduler_service import LotterySchedulerService

    async with AsyncSessionLocal() as db:
        svc = LotterySchedulerService(db, database_url=settings.database_url)
        result = await svc.tick(initiated_by="apscheduler")
        await db.commit()
        logger.info(
            "lottery scheduler tick status=%s mode=%s wrote=%s blocked=%s",
            result.status,
            result.mode,
            result.wrote,
            result.blocked_reason,
        )


def start_lottery_scheduler() -> AsyncIOScheduler | None:
    """Start only when explicitly enabled — default disabled."""
    global _scheduler, _shutting_down
    _shutting_down = False
    if not settings.lottery_scheduler_enabled:
        logger.info("Lottery scheduler not started (LOTTERY_SCHEDULER_ENABLED=false)")
        return None
    if (settings.lottery_scheduler_mode or "disabled").lower() == "disabled":
        logger.info("Lottery scheduler not started (mode=disabled)")
        return None
    if _scheduler is not None:
        return _scheduler

    minutes = max(1, int(settings.lottery_sync_interval_minutes))
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _lottery_scheduler_tick,
        "interval",
        minutes=minutes,
        id="lottery_sync_tick",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Lottery scheduler started interval=%sm mode=%s", minutes, settings.lottery_scheduler_mode)
    return _scheduler


def stop_lottery_scheduler() -> None:
    global _scheduler, _shutting_down
    _shutting_down = True
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Lottery scheduler stopped")


def lottery_scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running
