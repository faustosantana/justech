"""Tests — Microsoft 365 Operativo (Fase 6)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD
from app.services.m365_email_classifier import M365EmailClassifier
from app.services.m365_email_extraction_service import M365EmailExtractionService
from app.services.m365_sharepoint_archive_service import M365SharePointArchiveService


def test_classify_dell_quote():
    clf = M365EmailClassifier()
    result = clf.classify(
        subject="Adjunto cotización Dell",
        body="Cotización Latitude Optiplex USD 12500 DGCP-2026-00125",
        sender_email="quotes@dell.com",
        attachment_names=["Cotizacion_Dell.pdf"],
    )
    assert result.classification == "cotizacion_proveedor"
    assert result.confidence >= 80


def test_extract_dell_entities():
    ext = M365EmailExtractionService()
    data = ext.extract(
        subject="Adjunto cotización Dell",
        body="Productos Latitude 5450, Optiplex, Monitor. USD 12,500. Banco Ademi. DGCP-2026-00125",
        sender_email="quotes@dell.com",
        sender_name="Dell",
        attachment_texts=[("cot.pdf", "Dell Latitude Optiplex Monitor USD 12500")],
    )
    assert data["vendor"] == "Dell"
    assert data["client"] == "Banco Ademi"
    assert data["amount"] == 12500
    assert data["currency"] == "USD"
    assert "Latitude" in " ".join(data["products"]) or any("latitude" in p.lower() for p in data["products"])
    assert data["dgcp_process_code"] == "DGCP-2026-00125"


def test_sharepoint_archive_path():
    svc = M365SharePointArchiveService()
    path = svc.build_path(
        classification="cotizacion_proveedor",
        vendor="Dell",
        client="Banco Ademi",
        dgcp_code="DGCP-2026-00125",
        filename="Cotizacion_Dell.pdf",
    )
    assert path.startswith("JAIOS_Corporativo/02_COTIZACIONES")
    assert "DGCP-2026-00125" in path


@pytest.mark.asyncio
async def test_operative_pipeline_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=120) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "tenant_slug": "justech"},
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible")
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/v1/m365/accounts/disconnect", headers=headers)

        sync = await client.post("/api/v1/m365/operative/sync", headers=headers)
        assert sync.status_code == 200, sync.text
        body = sync.json()
        assert body["ingested"] >= 1

        dash = await client.get("/api/v1/m365/operative/dashboard", headers=headers)
        assert dash.status_code == 200
        assert dash.json()["quotes_detected"] >= 1

        emails = await client.get("/api/v1/m365/operative/emails", headers=headers)
        assert emails.status_code == 200
        items = emails.json()["items"]
        assert len(items) >= 1
        dell = next((e for e in items if "Dell" in e["subject"]), items[0])
        assert dell["suggested_actions"]
        assert dell["extracted_data"].get("vendor") or dell["classification"]

        action = await client.post(
            f"/api/v1/m365/operative/emails/{dell['id']}/actions",
            headers=headers,
            json={"action_key": "create_task", "params": {}},
        )
        assert action.status_code == 200, action.text
        assert action.json()["status"] == "ok"
        assert action.json().get("task_id")

        webhook = await client.post(
            "/api/v1/m365/operative/webhooks/n8n/inbound-email",
            headers=headers,
            json={
                "mailbox": "cotizaciones@justech.do",
                "subject": "Test n8n HP Quote",
                "sender_email": "quotes@hp.com",
                "body_text": "Cotización HP USD 5000",
            },
        )
        assert webhook.status_code == 200
