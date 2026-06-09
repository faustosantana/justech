"""Microsoft 365 Intelligence Center — interfaces futuras (Fase 4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class M365MailboxItem:
    subject: str
    sender: str
    received_at: datetime | None = None
    preview: str = ""
    web_link: str | None = None


@dataclass
class M365DriveItem:
    name: str
    path: str
    modified_at: datetime | None = None
    web_link: str | None = None
    mime_type: str | None = None


class M365IntelligenceSource(ABC):
    """Fuente de datos M365 (Graph API) — sin implementación en Fase 3."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @abstractmethod
    async def search_mail(self, query: str, *, limit: int = 20) -> list[M365MailboxItem]:
        pass

    @abstractmethod
    async def search_files(self, query: str, *, limit: int = 20) -> list[M365DriveItem]:
        pass
