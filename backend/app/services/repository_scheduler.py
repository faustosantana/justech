"""Scheduler — sincronización automática de repositorios OneDrive."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.integration_settings import IntegrationRepositoryBinding
from app.models.m365_account import M365UserAccount
from app.services.repository_sync_service import RepositorySyncService

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_repository_syncs() -> None:
    async with AsyncSessionLocal() as db:
        bindings = (
            await db.execute(
                select(IntegrationRepositoryBinding).where(
                    IntegrationRepositoryBinding.auto_sync.is_(True),
                    IntegrationRepositoryBinding.status.in_(("configured", "synced", "error")),
                )
            )
        ).scalars().all()
        if not bindings:
            return

        by_tenant: dict = {}
        for b in bindings:
            by_tenant.setdefault(b.tenant_id, []).append(b)

        for tenant_id, tenant_bindings in by_tenant.items():
            account = (
                await db.execute(
                    select(M365UserAccount)
                    .where(
                        M365UserAccount.tenant_id == tenant_id,
                        M365UserAccount.connection_status == "connected",
                    )
                    .order_by(M365UserAccount.last_sync_at.desc().nullslast())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if not account:
                continue
            svc = RepositorySyncService(db, tenant_id, user_id=account.jaios_user_id)
            for binding in tenant_bindings:
                try:
                    await svc.sync_binding(binding.id, trigger="scheduled")
                    logger.info("Repository sync ok tenant=%s binding=%s", tenant_id, binding.folder_key)
                except Exception:
                    logger.exception(
                        "Repository sync failed tenant=%s binding=%s",
                        tenant_id,
                        binding.folder_key,
                    )
        await db.commit()

    async with AsyncSessionLocal() as db2:
        from sqlalchemy import select as sel

        from app.models.tenant import Tenant
        from app.services.document_pending_service import DocumentPendingService

        for tenant in (await db2.execute(sel(Tenant))).scalars().all():
            try:
                pending = DocumentPendingService(db2, tenant.id)
                await pending.scan_and_upsert()
                await pending.auto_resolve()
            except Exception:
                logger.exception("Pending auto-resolve failed tenant=%s", tenant.id)
        await db2.commit()


def start_repository_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(_run_repository_syncs, "interval", minutes=15, id="repository_sync_check")
    _scheduler.start()
    logger.info("Repository scheduler started (15 min)")
    return _scheduler


def stop_repository_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Repository scheduler stopped")
