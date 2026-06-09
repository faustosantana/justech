"""Documentos unificados — indexación y búsqueda (futuro Qdrant)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from integrations.microsoft365.schemas import M365DocumentItem, M365SearchHit

if TYPE_CHECKING:
    from integrations.microsoft365.client import M365Client


class M365DocumentsService:
    def __init__(self, client: M365Client):
        self._client = client

    async def list_documents(self, *, search: str = "", limit: int = 50) -> list[M365DocumentItem]:
        return []

    async def search(self, query: str, *, limit: int = 25) -> list[M365SearchHit]:
        return []
