"""Cliente HTTP hacia el bridge Baileys (WhatsApp Web)."""

from __future__ import annotations

import httpx

from app.config import settings


class WhatsAppBridgeClient:
    def __init__(self) -> None:
        self.base_url = settings.whatsapp_bridge_url.rstrip("/")
        self.secret = settings.whatsapp_bridge_secret

    def _headers(self) -> dict[str, str]:
        return {"X-Bridge-Secret": self.secret}

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{self.base_url}/health")
            r.raise_for_status()
            return r.json()

    async def create_session(self, session_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/v1/sessions",
                json={"session_id": session_id},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def get_status(self, session_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.base_url}/v1/sessions/{session_id}/status",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def disconnect(self, session_id: str, logout: bool = True) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.delete(
                f"{self.base_url}/v1/sessions/{session_id}",
                params={"logout": str(logout).lower()},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def list_chats(self, session_id: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{self.base_url}/v1/sessions/{session_id}/chats",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json().get("items", [])

    async def list_messages(self, session_id: str, remote_jid: str, limit: int = 50) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{self.base_url}/v1/sessions/{session_id}/chats/{remote_jid}/messages",
                params={"limit": limit},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json().get("items", [])

    async def send_text(
        self,
        session_id: str,
        remote_jid: str,
        text: str,
        quoted_message_id: str | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/v1/sessions/{session_id}/chats/{remote_jid}/messages",
                json={"text": text, "quoted_message_id": quoted_message_id},
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    async def send_document(
        self,
        session_id: str,
        remote_jid: str,
        *,
        filename: str,
        mimetype: str,
        content_base64: str,
        caption: str | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/v1/sessions/{session_id}/chats/{remote_jid}/documents",
                json={
                    "filename": filename,
                    "mimetype": mimetype,
                    "content_base64": content_base64,
                    "caption": caption,
                },
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()
