import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.dgcp_schedule import DGCPSyncSchedule
from app.services.audit_service import AuditService
from app.services.dgcp_sync_service import DGCPSyncService

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_due_syncs() -> None:
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DGCPSyncSchedule).where(
                DGCPSyncSchedule.is_enabled.is_(True),
                DGCPSyncSchedule.next_run_at <= now,
            )
        )
        schedules = list(result.scalars().all())
        if not schedules:
            return

        for schedule in schedules:
            try:
                sync = DGCPSyncService(db)
                job = await sync.run_sync(
                    schedule.tenant_id,
                    trigger="scheduled",
                    max_pages=schedule.max_pages,
                    page_size=schedule.page_size,
                )
                audit = AuditService(db)
                await audit.log(
                    action="dgcp.sync.scheduled",
                    tenant_id=schedule.tenant_id,
                    resource_type="dgcp_sync_job",
                    resource_id=job.id,
                    details={
                        "created": job.created_count,
                        "updated": job.updated_count,
                        "pages": job.pages_synced,
                    },
                )
                logger.info(
                    "DGCP scheduled sync tenant=%s created=%s updated=%s",
                    schedule.tenant_id,
                    job.created_count,
                    job.updated_count,
                )
            except Exception:
                logger.exception("DGCP scheduled sync failed tenant=%s", schedule.tenant_id)
        await db.commit()


def start_dgcp_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(_run_due_syncs, "interval", minutes=5, id="dgcp_sync_check")
    _scheduler.start()
    logger.info("DGCP scheduler started")
    return _scheduler


def stop_dgcp_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("DGCP scheduler stopped")
