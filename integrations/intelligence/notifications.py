"""Notificaciones — interfaces futuras (Fase 5)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    TEAMS = "teams"


@dataclass
class NotificationPayload:
    tenant_id: UUID
    title: str
    body: str | None = None
    channel: NotificationChannel = NotificationChannel.IN_APP
    user_id: UUID | None = None
    source_module: str = ""
    source_event: str = ""
    data: dict = field(default_factory=dict)
    created_at: datetime | None = None


class NotificationDispatcher(ABC):
    @abstractmethod
    async def dispatch(self, notification: NotificationPayload) -> None:
        pass
