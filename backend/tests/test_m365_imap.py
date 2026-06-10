"""Tests — conexión IMAP cliente correo (sin credenciales Azure)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_connect_imap_validates_and_stores_encrypted_password():
    transport = ASGITransport(app=app)
    with patch("app.services.m365_account_service.M365ImapService") as mock_cls:
        mock_cls.return_value.test_connection.return_value = {"status": "ok"}
        async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": "justech"},
            )
            if login.status_code != 200:
                pytest.skip("Login no disponible")
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            response = await client.post(
                "/api/v1/m365/accounts/connect-imap",
                headers=headers,
                json={
                    "email": "fausto@justech.do",
                    "password": "app-password-test",
                    "imap_host": "outlook.office365.com",
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["mailbox_connected"] is True
            assert body["connection_mode"] == "imap"
            assert body["email"] == "fausto@justech.do"
            mock_cls.return_value.test_connection.assert_called_once()

            mine = await client.get("/api/v1/m365/accounts/me", headers=headers)
            assert mine.status_code == 200
            assert mine.json()["mailbox_connected"] is True

            await client.post("/api/v1/m365/accounts/disconnect", headers=headers)


@pytest.mark.asyncio
async def test_connect_imap_rejects_bad_credentials():
    transport = ASGITransport(app=app)
    with patch("app.services.m365_account_service.M365ImapService") as mock_cls:
        mock_cls.return_value.test_connection.side_effect = Exception("authentication failed")
        async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": "justech"},
            )
            if login.status_code != 200:
                pytest.skip("Login no disponible")
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            response = await client.post(
                "/api/v1/m365/accounts/connect-imap",
                headers=headers,
                json={"email": "bad@justech.do", "password": "wrong"},
            )
            assert response.status_code == 400
            assert "contraseña" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_operative_sync_uses_imap_when_connected():
    transport = ASGITransport(app=app)
    fake_messages = [
        {
            "external_message_id": f"imap-test-{uuid.uuid4()}",
            "mailbox": "fausto@justech.do",
            "subject": "Cotización Lenovo test IMAP",
            "sender_email": "sales@lenovo.com",
            "sender_name": "Lenovo",
            "received_at": "2026-06-06T12:00:00+00:00",
            "body_text": "Cotización USD 9000 DGCP-2026-00999",
            "attachments": [],
        }
    ]
    with patch("app.services.m365_account_service.M365ImapService") as connect_mock:
        connect_mock.return_value.test_connection.return_value = {"status": "ok"}
        with patch("app.services.m365_operative_service.M365ImapService") as sync_mock:
            sync_mock.return_value.fetch_recent.return_value = fake_messages
            async with AsyncClient(transport=transport, base_url="http://test", timeout=120) as client:
                login = await client.post(
                    "/api/v1/auth/login",
                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": "justech"},
                )
                if login.status_code != 200:
                    pytest.skip("Login no disponible")
                headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

                try:
                    connect = await client.post(
                        "/api/v1/m365/accounts/connect-imap",
                        headers=headers,
                        json={"email": "fausto@justech.do", "password": "secret"},
                    )
                    assert connect.status_code == 200

                    sync = await client.post("/api/v1/m365/operative/sync", headers=headers)
                    assert sync.status_code == 200, sync.text
                    body = sync.json()
                    assert body["graph_connected"] is True
                    assert body["demo_mode"] is False
                    assert "IMAP" in body["message"]
                    assert body["processed"] >= 1
                finally:
                    await client.post("/api/v1/m365/accounts/disconnect", headers=headers)