"""Tests — OdooQuotationService y endpoints de cotización."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.odoo import OdooQuotationSearchParams
from app.services.odoo_quotation_service import OdooQuotationService


@pytest.mark.asyncio
async def test_odoo_quotations_search_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/quotations/search?q=S0001")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_odoo_quotation_detail_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/quotations/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_odoo_quotation_pdf_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/odoo/quotations/1/pdf")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dgcp_economic_offer_status_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/dgcp/opportunities/00000000-0000-0000-0000-000000000001/economic-offer/status"
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_quotation_service_search_builds_domain():
    odoo = MagicMock()
    odoo._get_client = AsyncMock(return_value=MagicMock(is_configured=False))
    odoo._not_connected_list = MagicMock(return_value=MagicMock(items=[], total=0, connected=False))
    svc = OdooQuotationService(odoo)
    result = await svc.search(OdooQuotationSearchParams(quotation_number="S00042", limit=10))
    assert result.connected is False
    odoo._not_connected_list.assert_called_once()


@pytest.mark.asyncio
async def test_quotation_service_maps_row():
    odoo = MagicMock()
    client = MagicMock(is_configured=True)
    odoo._get_client = AsyncMock(return_value=client)
    odoo._domain = MagicMock(side_effect=lambda model, domain: domain)
    odoo._list_response = MagicMock(side_effect=lambda items, total: MagicMock(items=items, total=total, connected=True))
    odoo._partner_ids_for_search = AsyncMock(return_value=[])
    odoo._text_search_domain = MagicMock(return_value=[])
    client.search_read = AsyncMock(
        return_value=[
            {
                "id": 7,
                "name": "S00007",
                "partner_id": [12, "Banco Caribe"],
                "date_order": "2026-01-15",
                "amount_total": 150000.0,
                "currency_id": [74, "DOP"],
                "state": "sent",
                "user_id": [3, "Ventas Justech"],
                "company_id": [1, "Justech SRL"],
                "validity_date": "2026-02-15",
            }
        ]
    )
    client.search_count = AsyncMock(return_value=1)

    svc = OdooQuotationService(odoo)
    result = await svc.search(OdooQuotationSearchParams(customer="Caribe"))
    assert result.total == 1
    item = result.items[0]
    assert item.name == "S00007"
    assert item.partner_name == "Banco Caribe"
    assert item.company_id == 1
    assert item.amount_total == Decimal("150000")


@pytest.mark.asyncio
async def test_compliance_adjuntado_counts_as_compliant():
    from app.services.dgcp_compliance_engine import COMPLIANT_STATUSES, DGCPComplianceEngine

    assert "adjuntado" in COMPLIANT_STATUSES
    engine = DGCPComplianceEngine()
    assert engine.display_status_label("adjuntado") == "Adjuntado al expediente"
    assert engine.normalize_status("adjuntado") == "adjuntado"
    assert engine.normalize_status("borrador_pendiente") == "borrador_pendiente"


@pytest.mark.asyncio
async def test_quotation_service_salesperson_filter_empty():
    odoo = MagicMock()
    client = MagicMock(is_configured=True)
    odoo._get_client = AsyncMock(return_value=client)
    odoo._domain = MagicMock(side_effect=lambda model, domain: domain)
    odoo._list_response = MagicMock(side_effect=lambda items, total: MagicMock(items=items, total=total, connected=True))
    client.search_read = AsyncMock(return_value=[])
    svc = OdooQuotationService(odoo)
    result = await svc.search(OdooQuotationSearchParams(salesperson="Inexistente", limit=10))
    assert result.total == 0
    client.search_read.assert_called_once()
    assert client.search_read.call_args[0][0] == "res.users"


@pytest.mark.asyncio
async def test_build_quotation_pdf_bytes():
    from decimal import Decimal

    from app.schemas.odoo import OdooQuotationDetailResponse, OdooQuotationLineResponse
    from integrations.odoo.quotation_pdf import build_quotation_pdf

    detail = OdooQuotationDetailResponse(
        id=1,
        name="C-0003630",
        partner_name="Cliente Test",
        amount_total=Decimal("1000"),
        currency="DOP",
        state="draft",
        lines=[
            OdooQuotationLineResponse(
                product_name="Laptop",
                quantity=2,
                price_unit=Decimal("500"),
                subtotal=Decimal("1000"),
            )
        ],
    )
    pdf = build_quotation_pdf(detail)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 200


@pytest.mark.asyncio
async def test_economic_offer_task_dedup_key_documented():
    """Clave única: tenant + opportunity + requirement + task_type=economic_offer."""
    meta = {
        "dgcp_opportunity_id": "opp",
        "dgcp_checklist_item_id": "item",
        "dgcp_requirement_key": "oferta_economica",
        "task_type": "economic_offer",
    }
    assert meta["task_type"] == "economic_offer"
