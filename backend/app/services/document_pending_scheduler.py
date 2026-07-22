"""Scheduler — escaneo de pendientes, auto-cierre y recordatorios."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_pending_maintenance() -> None:
    from app.services.document_pending_reminder_service import DocumentPendingReminderService
    from app.services.document_pending_service import DocumentPendingService

    async with AsyncSessionLocal() as db:
        tenants = (await db.execute(select(Tenant))).scalars().all()
        totals = {"scanned": 0, "resolved": 0, "reminders": 0, "escalations": 0}
        for tenant in tenants:
            pending = DocumentPendingService(db, tenant.id)
            created = await pending.scan_and_upsert()
            resolved = await pending.auto_resolve()
            reminder_svc = DocumentPendingReminderService(db, tenant.id)
            rem = await reminder_svc.process_due_reminders()
            totals["scanned"] += created
            totals["resolved"] += resolved
            totals["reminders"] += rem["reminders"]
            totals["escalations"] += rem["escalations"]
        logger.info("Document pending maintenance: %s", totals)


def start_document_pending_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(_run_pending_maintenance, "interval", hours=6, id="document_pending_maintenance")
    _scheduler.start()
    logger.info("Document pending scheduler started (6h)")
    return _scheduler


def stop_document_pending_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Document pending scheduler stopped")
