"""Outlook Calendar — eventos (futuro)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from integrations.microsoft365.schemas import M365CalendarEvent

if TYPE_CHECKING:
    from integrations.microsoft365.client import M365Client


class M365CalendarService:
    def __init__(self, client: M365Client):
        self._client = client

    async def list_events(self, *, limit: int = 50) -> list[M365CalendarEvent]:
        return []
