"""Standalone Lottery Sync Worker — own lifecycle, independent of API web process.

Usage:
  python -m app.lottery.sync.worker

When LOTTERY_SYNC_WORKER_STANDALONE=true, the API must NOT start APScheduler.

Also hosts the Lottery AI alert detector on an independent cadence (same process,
no parallel cron / no second scheduler).
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
_ai_alert_last_run_at: datetime | None = None


def _handle_signal(signum, frame) -> None:  # noqa: ARG001
    global _shutting_down
    logger.info("signal=%s shutting down", signum)
    _shutting_down = True


async def _tick_once() -> dict:
    global _ai_alert_last_run_at
    from app.config import settings
    from app.db.session import AsyncSessionLocal
    from app.lottery.sync.dispatcher import dispatch_status
    from app.services.lottery_ai_alert_detector import maybe_run_detector_tick
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
            # Still allow AI detector cadence when sync scheduler disabled
            det, _ai_alert_last_run_at = await maybe_run_detector_tick(
                db, last_run_at=_ai_alert_last_run_at
            )
            if det:
                logger.info(
                    "ai_alert_detector status=%s findings=%s auto_resolved=%s skipped=%s",
                    det.status,
                    det.findings,
                    det.auto_resolved,
                    det.skipped_reason,
                )
            await db.commit()
            return {"status": "planner_only", "ai_alerts": det.status if det else "deferred", **status}

        mode = (settings.lottery_scheduler_mode or "disabled").lower()
        if mode == "disabled":
            det, _ai_alert_last_run_at = await maybe_run_detector_tick(
                db, last_run_at=_ai_alert_last_run_at
            )
            if det:
                logger.info(
                    "ai_alert_detector status=%s findings=%s skipped=%s",
                    det.status,
                    det.findings,
                    det.skipped_reason,
                )
            await db.commit()
            return {"status": "mode_disabled", "ai_alerts": det.status if det else "deferred", **status}

        svc = LotterySchedulerService(db, database_url=settings.database_url)
        result = await svc.tick(initiated_by="lottery-sync-worker")
        det, _ai_alert_last_run_at = await maybe_run_detector_tick(
            db, last_run_at=_ai_alert_last_run_at
        )
        if det:
            logger.info(
                "ai_alert_detector status=%s findings=%s auto_resolved=%s skipped=%s",
                det.status,
                det.findings,
                det.auto_resolved,
                det.skipped_reason,
            )
        await db.commit()
        return {
            "status": result.status,
            "mode": result.mode,
            "wrote": result.wrote,
            "blocked_reason": result.blocked_reason,
            "ai_alerts": det.status if det else "deferred",
            "windows": status,
        }


async def run_loop() -> None:
    from app.config import settings

    # Base cadence: 60s loop; window planner decides which lotteries are due.
    # Actual sync still goes through LotterySchedulerService (gates/locks/circuit).
    # AI alert detector uses independent next_run_at / last_run_at cadence.
    interval = max(30, min(300, int(os.environ.get("LOTTERY_SYNC_WORKER_LOOP_SECONDS", "60"))))
    logger.info(
        "worker start interval=%ss mode=%s standalone_hint=%s ai_detector=%s ai_interval=%ss",
        interval,
        settings.lottery_scheduler_mode,
        os.environ.get("LOTTERY_SYNC_WORKER_STANDALONE", "true"),
        settings.lottery_ai_alert_detector_enabled,
        settings.lottery_ai_alert_detector_interval_seconds,
    )
    while not _shutting_down:
        started = datetime.now(timezone.utc)
        try:
            out = await _tick_once()
            logger.info(
                "tick done status=%s ai_alerts=%s elapsed_ms=%s",
                out.get("status"),
                out.get("ai_alerts"),
                int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
            )
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
