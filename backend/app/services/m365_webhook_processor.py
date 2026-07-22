"""Procesamiento real de notificaciones Microsoft Graph."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.m365_operative_service import M365OperativeService
from app.services.m365_qdrant_service import M365QdrantService
from app.services.m365_repository_service import M365RepositoryService

logger = logging.getLogger(__name__)


class M365WebhookProcessor:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id

    async def process_notifications(self, items: list[dict]) -> dict:
        from app.models.m365_account import M365UserAccount
        from sqlalchemy import select

        processed = 0
        errors: list[str] = []

        acc_result = await self.db.execute(
            select(M365UserAccount).where(
                M365UserAccount.is_active.is_(True),
                M365UserAccount.connection_mode == "oauth",
            )
        )
        accounts = list(acc_result.scalars().all())

        for item in items:
            try:
                resource = item.get("resource", "")
                change_type = item.get("changeType", "")

                for acc in accounts:
                    tid = acc.tenant_id
                    uid = acc.jaios_user_id
                    if not uid:
                        continue
                    if "/messages" in resource:
                        await self._handle_mail_change(tid, uid)
                    elif "/events" in resource:
                        await self._handle_calendar_change(tid, resource, change_type)
                    elif "/drive" in resource or "/drives/" in resource:
                        await self._handle_drive_change(tid, uid, acc.id)
                processed += 1
            except Exception as exc:
                errors.append(str(exc)[:200])
                logger.warning("Webhook item failed: %s", exc)

        await self.db.commit()
        return {"processed": processed, "errors": errors}

    async def _handle_mail_change(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        svc = M365OperativeService(self.db, tenant_id, user_id)
        await svc.sync_inbox()

    async def _handle_calendar_change(self, tenant_id: uuid.UUID, resource: str, change_type: str) -> None:
        qdrant = M365QdrantService(tenant_id)
        qdrant.upsert_document(
            doc_id=resource,
            title=f"Evento calendario ({change_type})",
            text=resource,
            source="calendar_webhook",
            category="calendar",
        )

    async def _handle_drive_change(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, account_id: uuid.UUID
    ) -> None:
        repo = M365RepositoryService(self.db, tenant_id, user_id)
        await repo.sync_all(account_id=account_id)
