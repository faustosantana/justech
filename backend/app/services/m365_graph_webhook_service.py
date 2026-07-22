"""Suscripciones Microsoft Graph webhooks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from integrations.microsoft365.config import M365Config

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class M365GraphWebhookService:
    def __init__(self, config: M365Config, access_token: str):
        self.config = config
        self.access_token = access_token

    async def renew_mail_subscription(
        self, *, notification_url: str, client_state: str = ""
    ) -> dict:
        expires = (datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = {
            "changeType": "created,updated",
            "notificationUrl": notification_url,
            "resource": "/me/mailFolders('Inbox')/messages",
            "expirationDateTime": expires,
            "clientState": client_state or "jaios-m365",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{GRAPH_BASE}/subscriptions",
                json=body,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Graph subscription error {resp.status_code}: {resp.text[:500]}")
            return resp.json()
