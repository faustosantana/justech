"""Tests Fase 5 — Work Operations Center."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.assistant.router import AssistantRouter, AssistantSource
from app.main import app
from app.scripts.seed import ADMIN_EMAIL, ADMIN_PASSWORD

WORK_ENDPOINTS = [
    "/api/v1/tasks",
    "/api/v1/work",
    "/api/v1/notifications",
    "/api/v1/routing/preview",
]


@pytest.mark.parametrize("path", WORK_ENDPOINTS)
@pytest.mark.asyncio
async def test_work_endpoints_require_auth(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        if path.endswith("preview"):
            response = await client.post(path, json={"event_type": "cotizacion", "title": "Test"})
        else:
            response = await client.get(path)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tasks_from_event_route_not_parsed_as_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tasks/from-event",
            json={"source": "manual", "event_type": "cotizacion", "title": "Test"},
        )
    assert response.status_code == 401
    assert "int_parsing" not in response.text


def test_assistant_router_detects_work():
    sources = AssistantRouter.detect_sources("Muéstrame mis tareas vencidas", "/work")
    assert AssistantSource.WORK in sources


@pytest.mark.asyncio
async def test_work_operations_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            pytest.skip("Login no disponible")
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        preview = await client.post(
            "/api/v1/routing/preview",
            headers=headers,
            json={
                "event_type": "cotizacion",
                "title": "Solicitud de cotización cliente ABC",
                "description": "Cliente solicita cotización de equipos",
            },
        )
        assert preview.status_code == 200, preview.text
        body = preview.json()
        assert body["category"] == "cotizacion"
        assert body["department"] == "ventas"
        assert body["suggested_assignee_name"] == "Marieli"

        vendor_preview = await client.post(
            "/api/v1/routing/preview",
            headers=headers,
            json={
                "event_type": "factura_proveedor",
                "title": "Factura proveedor XYZ",
            },
        )
        assert vendor_preview.status_code == 200
        assert vendor_preview.json()["suggested_assignee_name"] == "Diana"

        from_event = await client.post(
            "/api/v1/tasks/from-event",
            headers=headers,
            json={
                "source": "manual",
                "event_type": "cotizacion",
                "title": "Cotización para cliente Demo QA",
                "description": "Prueba Fase 5",
                "customer_name": "Cliente Demo",
            },
        )
        assert from_event.status_code == 201, from_event.text
        task = from_event.json()
        assert task["category"] == "cotizacion"
        assert task["suggested_assignee_name"] == "Marieli"
        task_id = task["id"]

        comment = await client.post(
            f"/api/v1/tasks/{task_id}/comments",
            headers=headers,
            json={"comment": "Comentario QA Fase 5"},
        )
        assert comment.status_code == 200
        assert len(comment.json()["comments"]) >= 1

        checklist = await client.post(
            f"/api/v1/tasks/{task_id}/checklist",
            headers=headers,
            json={"text": "Validar requerimiento"},
        )
        assert checklist.status_code == 200
        items = checklist.json()["checklist_items"]
        assert any(i["text"] == "Validar requerimiento" for i in items)

        work = await client.get("/api/v1/work", headers=headers)
        assert work.status_code == 200

        notifs = await client.get("/api/v1/notifications", headers=headers)
        assert notifs.status_code == 200

        manual = await client.post(
            "/api/v1/tasks",
            headers=headers,
            json={
                "title": "Tarea manual QA",
                "priority": "alta",
                "category": "soporte",
                "department": "soporte",
            },
        )
        assert manual.status_code == 201

        update = await client.put(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
            json={"status": "en_proceso"},
        )
        assert update.status_code == 200
        assert update.json()["status"] == "en_proceso"

        users = await client.get("/api/v1/users", headers=headers)
        assert users.status_code == 200
        user_list = users.json()["items"]
        assert len(user_list) >= 1
        marieli = next((u for u in user_list if "Marieli" in u["full_name"]), None)

        if marieli:
            assign = await client.put(
                f"/api/v1/tasks/{task_id}",
                headers=headers,
                json={"assigned_to_id": marieli["id"]},
            )
            assert assign.status_code == 200
            body = assign.json()
            assert body["assigned_to_id"] == marieli["id"]
            assert body["assigned_to_name"] == marieli["full_name"]
            assert body["assigned_to_email"] == marieli["email"]

        preview_sup = await client.post(
            "/api/v1/routing/preview",
            headers=headers,
            json={"event_type": "cotizacion", "title": "Cotización cliente"},
        )
        assert preview_sup.status_code == 200
        assert preview_sup.json().get("suggested_supervisor_name") == "Fausto"
