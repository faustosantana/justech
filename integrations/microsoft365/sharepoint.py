"""SharePoint Online — sitios y bibliotecas (futuro)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from integrations.microsoft365.schemas import M365SharePointSite

if TYPE_CHECKING:
    from integrations.microsoft365.client import M365Client


class M365SharePointService:
    def __init__(self, client: M365Client):
        self._client = client

    async def list_sites(self, *, search: str = "", limit: int = 50) -> list[M365SharePointSite]:
        return []
