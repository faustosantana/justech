"""Notificaciones Microsoft Teams + n8n."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.notification_service import NotificationService
from integrations.n8n import N8nClient


class M365TeamsNotificationService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._notifications = NotificationService(db, tenant_id, user_id)

    async def notify_email_processed(
        self,
        *,
        user_id: uuid.UUID,
        title: str,
        message: str,
        email_id: uuid.UUID,
        severity: str = "info",
    ) -> uuid.UUID | None:
        notif = await self._notifications.create(
            user_id=user_id,
            title=title,
            message=message,
            type="m365_email",
            severity=severity,
            related_entity_type="m365_email",
            related_entity_id=str(email_id),
        )
        await self._trigger_n8n(
            workflow_id=settings.m365_n8n_teams_workflow or "m365-teams-notify",
            payload={"title": title, "message": message, "email_id": str(email_id)},
        )
        return notif.id

    async def _trigger_n8n(self, *, workflow_id: str, payload: dict) -> bool:
        if not settings.m365_n8n_enabled:
            return False
        try:
            client = N8nClient(tenant_id=str(self.tenant_id))
            result = await client.trigger_workflow(workflow_id, payload=payload)
            return bool(result.get("triggered"))
        except Exception:
            return False
