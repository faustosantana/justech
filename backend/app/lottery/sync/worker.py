"""Standalone Lottery Sync Worker — own lifecycle, independent of API web process.

Usage:
  python -m app.lottery.sync.worker

When LOTTERY_SYNC_WORKER_STANDALONE=true, the API must NOT start APScheduler.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [lottery-sync-worker] %(message)s")
logger = logging.getLogger("lottery.sync.worker")

_shutting_down = False


def _handle_signal(signum, frame) -> None:  # noqa: ARG001
    global _shutting_down
    logger.info("signal=%s shutting down", signum)
    _shutting_down = True


async def _tick_once() -> dict:
    from app.config import settings
    from app.db.session import AsyncSessionLocal
    from app.lottery.sync.dispatcher import dispatch_status
    from app.services.lottery_scheduler_service import LotterySchedulerService

    async with AsyncSessionLocal() as db:
        status = await dispatch_status(db)
        logger.info(
            "windows phases=%s due=%s auto_write=%s",
            status.get("phases"),
            len(status.get("sync_enabled_due") or []),
            status.get("auto_write_lotteries"),
        )
        if not settings.lottery_scheduler_enabled:
            logger.info("scheduler disabled — window plan only")
            await db.commit()
            return {"status": "planner_only", **status}

        mode = (settings.lottery_scheduler_mode or "disabled").lower()
        if mode == "disabled":
            await db.commit()
            return {"status": "mode_disabled", **status}

        svc = LotterySchedulerService(db, database_url=settings.database_url)
        result = await svc.tick(initiated_by="lottery-sync-worker")
        await db.commit()
        return {
            "status": result.status,
            "mode": result.mode,
            "wrote": result.wrote,
            "blocked_reason": result.blocked_reason,
            "windows": status,
        }


async def run_loop() -> None:
    from app.config import settings

    # Base cadence: 60s loop; window planner decides which lotteries are due.
    # Actual sync still goes through LotterySchedulerService (gates/locks/circuit).
    interval = max(30, min(300, int(os.environ.get("LOTTERY_SYNC_WORKER_LOOP_SECONDS", "60"))))
    logger.info(
        "worker start interval=%ss mode=%s standalone_hint=%s",
        interval,
        settings.lottery_scheduler_mode,
        os.environ.get("LOTTERY_SYNC_WORKER_STANDALONE", "true"),
    )
    while not _shutting_down:
        started = datetime.now(timezone.utc)
        try:
            out = await _tick_once()
            logger.info("tick done status=%s elapsed_ms=%s", out.get("status"), int((datetime.now(timezone.utc) - started).total_seconds() * 1000))
        except Exception:
            logger.exception("tick failed")
        for _ in range(interval):
            if _shutting_down:
                break
            await asyncio.sleep(1)
    logger.info("worker stopped")


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
