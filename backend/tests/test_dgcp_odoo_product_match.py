"""Unit tests for DGCP ↔ Odoo product matching states."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.dgcp_odoo_product_match_service import (
    CONF_EXACT_REF,
    STATUS_MATCHED,
    STATUS_REVIEW,
    STATUS_UNMATCHED,
    DGCPOdooProductMatchService,
)


def _opp(lines=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        code="UAT-MATCH-001",
        currency="DOP",
        full_info={"dgcp_line_items": lines or []},
    )


@pytest.mark.asyncio
async def test_match_exact_reference_matched():
    svc = DGCPOdooProductMatchService(db=AsyncMock(), tenant_id=uuid.uuid4(), user_id=uuid.uuid4())
    client = MagicMock()
    client.search_read = AsyncMock(
        return_value=[{"id": 10, "name": "Switch Cisco", "default_code": "C9200L-24P-4G", "barcode": False, "list_price": 100, "display_name": "C9200L-24P-4G"}]
    )
    result = await svc.match_line(
        client,
        {
            "line_number": 1,
            "description": "Switch Cisco C9200L-24P-4G",
            "reference": "C9200L-24P-4G",
            "quantity": 2,
        },
    )
    assert result["status"] == STATUS_MATCHED
    assert result["suggested_product_id"] == 10
    assert result["confidence"] >= CONF_EXACT_REF


@pytest.mark.asyncio
async def test_match_ambiguous_review_required():
    svc = DGCPOdooProductMatchService(db=AsyncMock(), tenant_id=uuid.uuid4(), user_id=uuid.uuid4())
    client = MagicMock()

    async def _sr(model, domain, fields, limit=5):
        # name exact returns multiple
        return [
            {"id": 1, "name": "Laptop 15 i7 A", "default_code": "LAP-A", "barcode": False, "list_price": 1, "display_name": "Laptop 15 i7 A"},
            {"id": 2, "name": "Laptop 15 i7 B", "default_code": "LAP-B", "barcode": False, "list_price": 1, "display_name": "Laptop 15 i7 B"},
        ]

    client.search_read = AsyncMock(side_effect=_sr)
    result = await svc.match_line(
        client,
        {"line_number": 2, "description": "Laptop 15 i7", "reference": "", "quantity": 1},
    )
    assert result["status"] == STATUS_REVIEW
    assert len(result["candidates"]) >= 2


@pytest.mark.asyncio
async def test_match_unmatched():
    svc = DGCPOdooProductMatchService(db=AsyncMock(), tenant_id=uuid.uuid4(), user_id=uuid.uuid4())
    client = MagicMock()
    client.search_read = AsyncMock(return_value=[])
    result = await svc.match_line(
        client,
        {"line_number": 3, "description": "Cable especial X inexistente ZZ99", "reference": "ZZ-NO-EXIST", "quantity": 1},
    )
    assert result["status"] == STATUS_UNMATCHED
    assert not result.get("suggested_product_id")


@pytest.mark.asyncio
async def test_approve_and_approved_lines_only():
    svc = DGCPOdooProductMatchService(db=AsyncMock(), tenant_id=uuid.uuid4(), user_id=uuid.uuid4())
    opp = _opp()
    opp.full_info = {
        "odoo_product_matches": {
            "lines": [
                {
                    "line_number": 1,
                    "status": STATUS_MATCHED,
                    "suggested_product_id": 10,
                    "confidence": 0.98,
                    "approved": False,
                },
                {
                    "line_number": 2,
                    "status": STATUS_REVIEW,
                    "suggested_product_id": 20,
                    "confidence": 0.7,
                    "approved": False,
                },
            ]
        }
    }
    assert svc.approved_matched_lines(opp) == []
    svc.approve_line(opp, line_number=1, approve=True, user_id=uuid.uuid4(), user_name="Fausto")
    approved = svc.approved_matched_lines(opp)
    assert len(approved) == 1
    assert approved[0]["line_number"] == 1
