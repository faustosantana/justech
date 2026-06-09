"""Tests — acciones DGCP reales: validación, notas, tareas, separación repositorios."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.task import Task
from tests.dgcp_test_helpers import (
    analyze_with_interest,
    ensure_operational_interest,
    find_opportunity_for_expediente_test,
)


async def _auth_headers() -> dict[str, str] | None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@justech.do",
                "password": "JaiosAdmin2026!",
                "tenant_slug": "justech",
            },
        )
        if login.status_code != 200:
            return None
        return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _first_opportunity(headers: dict[str, str]) -> str | None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_res = await client.get("/api/v1/dgcp/opportunities?limit=1", headers=headers)
        if list_res.status_code != 200 or not list_res.json()["items"]:
            return None
        return list_res.json()["items"][0]["id"]


@pytest.mark.asyncio
async def test_process_documents_exclude_corporate_knowledge():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")
    opp_id = await _first_opportunity(headers)
    if not opp_id:
        pytest.skip("Sin oportunidades DGCP")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        analyze = await analyze_with_interest(client, opp_id, headers)
        proc = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}/process-documents", headers=headers)
        assert proc.status_code == 200
        for item in proc.json()["items"]:
            assert item["source_type"] != "knowledge_copy"
            assert not str(item["title"]).startswith("[Corpus legal]")
            assert item["source_type"] in (
                "portal",
                "dgcp_api",
                "portal_text",
                "process_file",
                "reference",
            )


@pytest.mark.asyncio
async def test_analyze_rejected_without_interest():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")
    opp_id = await _first_opportunity(headers)
    if not opp_id:
        pytest.skip("Sin oportunidades DGCP")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        opp = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}", headers=headers)
        if opp.json().get("status") not in ("detected", "to_review"):
            pytest.skip("Oportunidad ya tiene interés — use otra para probar rechazo")

        analyze = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/requirements/analyze",
            headers=headers,
        )
        assert analyze.status_code == 400
        assert "Mostrar interés" in analyze.json()["detail"]


@pytest.mark.asyncio
async def test_expediente_sin_preparar_after_interest_before_licitar():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        opp_id = await find_opportunity_for_expediente_test(client, headers)
        if not opp_id:
            pytest.skip("Sin oportunidad DGCP limpia para expediente sin_preparar")

        await ensure_operational_interest(client, opp_id, headers)
        opp = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}", headers=headers)
        status = opp.json()["status"]
        assert status in ("interested", "to_bid", "won", "lost")
        if status != "interested":
            pytest.skip("Oportunidad ya pasó a Licitar — expediente puede estar activo")

        pre = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/status",
            headers=headers,
        )
        if pre.status_code == 200 and pre.json().get("expediente_status") != "sin_preparar":
            pytest.skip("Expediente ya preparado en otra prueba")

        analyze = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/requirements/analyze",
            headers=headers,
        )
        assert analyze.status_code == 200, analyze.text
        exp = await client.get(
            f"/api/v1/dgcp/opportunities/{opp_id}/bid-package/status",
            headers=headers,
        )
        assert exp.status_code == 200
        assert exp.json()["expediente_status"] == "sin_preparar"


@pytest.mark.asyncio
async def test_manual_validation_persists_and_recalculates():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")
    opp_id = await _first_opportunity(headers)
    if not opp_id:
        pytest.skip("Sin oportunidades DGCP")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await analyze_with_interest(client, opp_id, headers)
        checklist = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}/checklist", headers=headers)
        items = checklist.json()["items"]
        item = next(
            (i for i in items if i.get("document_id") or i.get("knowledge_asset_id")),
            items[0],
        )
        item_id = item["id"]
        prev_status = item["status"]
        has_doc = bool(item.get("document_id") or item.get("knowledge_asset_id"))
        validate_payload = {
            "status": "validado_manual" if has_doc else "no_aplica",
            "note": "Revisado en QA — persistencia DB.",
        }

        validate = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{item_id}/manual-validation",
            headers=headers,
            json=validate_payload,
        )
        assert validate.status_code == 200, validate.text
        body = validate.json()
        assert body["new_status"] == validate_payload["status"]
        assert body["previous_status"] == prev_status
        assert body["bid_package"]["preparation_pct"] >= 0

        async with AsyncSessionLocal() as session:
            pkg = (
                await session.execute(
                    select(DGCPBidPackage).where(DGCPBidPackage.opportunity_id == uuid.UUID(opp_id))
                )
            ).scalar_one()
            stored = next(i for i in pkg.checklist if str(i["id"]) == item_id)
            assert stored["status"] == validate_payload["status"]
            assert stored.get("manual_validation", {}).get("validated_by")
            assert stored.get("note_history")

            audits = (
                await session.execute(
                    select(AuditLog).where(
                        AuditLog.action == "dgcp.checklist.manual_validation",
                        AuditLog.resource_id == pkg.id,
                    )
                )
            ).scalars().all()
            assert audits


@pytest.mark.asyncio
async def test_add_note_persists_history():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")
    opp_id = await _first_opportunity(headers)
    if not opp_id:
        pytest.skip("Sin oportunidades DGCP")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await analyze_with_interest(client, opp_id, headers)
        checklist = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}/checklist", headers=headers)
        item_id = checklist.json()["items"][0]["id"]

        note = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{item_id}/notes",
            headers=headers,
            json={"note": "Nota de seguimiento — persistencia DB."},
        )
        assert note.status_code == 200, note.text
        history = note.json()["note_history"]
        assert len(history) >= 1
        assert history[-1]["note"] == "Nota de seguimiento — persistencia DB."
        assert history[-1]["author"]

        async with AsyncSessionLocal() as session:
            pkg = (
                await session.execute(
                    select(DGCPBidPackage).where(DGCPBidPackage.opportunity_id == uuid.UUID(opp_id))
                )
            ).scalar_one()
            stored = next(i for i in pkg.checklist if str(i["id"]) == item_id)
            assert stored.get("notes") == "Nota de seguimiento — persistencia DB."
            assert len(stored.get("note_history") or []) >= 1


@pytest.mark.asyncio
async def test_create_checklist_task_links_and_dedupes():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")
    opp_id = await _first_opportunity(headers)
    if not opp_id:
        pytest.skip("Sin oportunidades DGCP")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await analyze_with_interest(client, opp_id, headers)
        checklist = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}/checklist", headers=headers)
        item_id = checklist.json()["items"][0]["id"]

        first = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{item_id}/task",
            headers=headers,
        )
        assert first.status_code == 200, first.text
        task_id = first.json()["task_id"]

        second = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{item_id}/task",
            headers=headers,
        )
        assert second.status_code == 200
        assert second.json()["task_id"] == task_id
        assert second.json().get("existing") is True

        async with AsyncSessionLocal() as session:
            pkg = (
                await session.execute(
                    select(DGCPBidPackage).where(DGCPBidPackage.opportunity_id == uuid.UUID(opp_id))
                )
            ).scalar_one()
            stored = next(i for i in pkg.checklist if str(i["id"]) == item_id)
            assert stored.get("task_id") == task_id

            task = await session.get(Task, uuid.UUID(task_id))
            assert task is not None
            assert task.metadata_.get("dgcp_checklist_item_id") == item_id


@pytest.mark.asyncio
async def test_manual_validation_rejected_without_document():
    headers = await _auth_headers()
    if not headers:
        pytest.skip("Login no disponible")
    opp_id = await _first_opportunity(headers)
    if not opp_id:
        pytest.skip("Sin oportunidades DGCP")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await analyze_with_interest(client, opp_id, headers)
        checklist = await client.get(f"/api/v1/dgcp/opportunities/{opp_id}/checklist", headers=headers)
        bare = next(
            (
                i
                for i in checklist.json()["items"]
                if not i.get("document_id") and not i.get("knowledge_asset_id")
            ),
            None,
        )
        if not bare:
            pytest.skip("Todos los ítems tienen documento — no se puede probar rechazo")

        validate = await client.post(
            f"/api/v1/dgcp/opportunities/{opp_id}/checklist/{bare['id']}/manual-validation",
            headers=headers,
            json={"status": "validado_manual", "note": "Intento inválido sin documento"},
        )
        assert validate.status_code == 400
        assert "documento" in validate.json()["detail"].lower()
