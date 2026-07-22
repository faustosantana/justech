"""Contactos Outlook vía Graph."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from integrations.microsoft365.graph_helpers import graph_list

if TYPE_CHECKING:
    from integrations.microsoft365.client import M365Client


class M365Contact(BaseModel):
    id: str | None = None
    display_name: str = ""
    email: str = ""
    company: str | None = None


class M365ContactsService:
    def __init__(self, client: M365Client):
        self._client = client

    async def list_contacts(self, *, search: str = "", limit: int = 50) -> list[M365Contact]:
        params: dict = {}
        if search.strip():
            params["$search"] = f'"{search.strip()}"'
        return await graph_list(
            self._client,
            "/me/contacts",
            limit=limit,
            params=params,
            map_row=lambda row: M365Contact(
                id=row.get("id"),
                display_name=row.get("displayName") or "",
                email=((row.get("emailAddresses") or [{}])[0]).get("address") or "",
                company=(row.get("companyName") or None),
            ),
        )
