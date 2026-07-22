"""Escritura de calendario M365 — CRUD Graph."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.m365_intelligence import M365CalendarActionResponse, M365CalendarEventCreate, M365CalendarEventUpdate
from app.services.m365_graph_errors import graph_error_message
from app.services.m365_graph_session import M365GraphSessionService
from integrations.microsoft365.errors import GraphError

_WRITE_BLOCKED = "Operación de escritura bloqueada por configuración del sistema"


class M365CalendarWriteService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._sessions = M365GraphSessionService(db, tenant_id, user_id)

    def _blocked(self) -> M365CalendarActionResponse | None:
        if settings.m365_read_only:
            return M365CalendarActionResponse(ok=False, message=_WRITE_BLOCKED)
        return None

    async def create_event(
        self, payload: M365CalendarEventCreate, *, account_id: uuid.UUID | None = None
    ) -> M365CalendarActionResponse:
        if blocked := self._blocked():
            return blocked
        try:
            sess = await self._sessions.session_for_account(account_id)
            ev = await sess.client.calendar.create_event(
                subject=payload.subject,
                start=payload.start,
                end=payload.end,
                location=payload.location,
                body=payload.body,
                attendees=payload.attendees,
                is_online=payload.is_online,
            )
        except (GraphError, PermissionError) as exc:
            msg = _WRITE_BLOCKED if isinstance(exc, PermissionError) else graph_error_message(exc)
            return M365CalendarActionResponse(ok=False, message=msg)
        return M365CalendarActionResponse(ok=True, message="Evento creado", event_id=ev.id)

    async def update_event(
        self, event_id: str, payload: M365CalendarEventUpdate, *, account_id: uuid.UUID | None = None
    ) -> M365CalendarActionResponse:
        if blocked := self._blocked():
            return blocked
        fields = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not fields:
            return M365CalendarActionResponse(ok=False, message="Sin cambios")
        try:
            sess = await self._sessions.session_for_account(account_id)
            await sess.client.calendar.update_event(event_id, **fields)
        except (GraphError, PermissionError) as exc:
            msg = _WRITE_BLOCKED if isinstance(exc, PermissionError) else graph_error_message(exc)
            return M365CalendarActionResponse(ok=False, message=msg)
        return M365CalendarActionResponse(ok=True, message="Evento actualizado", event_id=event_id)

    async def delete_event(self, event_id: str, *, account_id: uuid.UUID | None = None) -> M365CalendarActionResponse:
        if blocked := self._blocked():
            return blocked
        try:
            sess = await self._sessions.session_for_account(account_id)
            await sess.client.calendar.cancel_event(event_id)
        except (GraphError, PermissionError) as exc:
            msg = _WRITE_BLOCKED if isinstance(exc, PermissionError) else graph_error_message(exc)
            return M365CalendarActionResponse(ok=False, message=msg)
        return M365CalendarActionResponse(ok=True, message="Evento eliminado", event_id=event_id)
