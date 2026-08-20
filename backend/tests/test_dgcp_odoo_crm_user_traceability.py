"""Unit tests for JAIOS user identity rules in DGCP→Odoo CRM bridge."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.dgcp_odoo_crm_bridge import DGCPOdooCrmBridge, _INITIATOR_PAYLOAD_KEYS


def _opp(**kwargs):
    base = dict(
        id=uuid.uuid4(),
        code="TEST-DGCP-001",
        title="Proceso test",
        institution="Entidad Test SA",
        company="justech",
        amount=1000,
        currency="DOP",
        status="preparing",
        deadline=None,
        source_url="https://example.com",
        created_at=None,
        full_info={},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_actor_identity_from_auth_user():
    uid = uuid.uuid4()
    bridge = DGCPOdooCrmBridge(db=AsyncMock(), tenant_id=uuid.uuid4(), user_id=uid)
    user = SimpleNamespace(id=uid, full_name="Fausto Santana", email="fausto@justech.do")
    with patch.object(bridge, "_load_user", AsyncMock(return_value=user)):
        ident = await bridge._actor_identity()
    assert ident["id"] == str(uid)
    assert ident["name"] == "Fausto Santana"
    assert ident["email"] == "fausto@justech.do"


@pytest.mark.asyncio
async def test_initiator_immutable_on_crm_vals():
    uid_a = uuid.uuid4()
    uid_b = uuid.uuid4()
    bridge = DGCPOdooCrmBridge(db=AsyncMock(), tenant_id=uuid.uuid4(), user_id=uid_b)
    opp = _opp()

    async def fake_fields(_client):
        return {
            "x_justech_jaios_user_id",
            "x_justech_jaios_user_name",
            "x_justech_jaios_owner_id",
            "x_justech_jaios_owner_name",
            "x_justech_dgcp_code",
            "x_justech_jaios_id",
            "x_justech_company_key",
        }

    with (
        patch.object(bridge, "_crm_fields", fake_fields),
        patch.object(bridge, "_rpe_for_company", AsyncMock(return_value="77671")),
        patch.object(
            bridge,
            "_actor_identity",
            AsyncMock(return_value={"id": str(uid_b), "name": "User B", "email": "b@x.com"}),
        ),
        patch.object(
            bridge,
            "_owner_identity",
            AsyncMock(return_value={"id": str(uid_b), "name": "User B", "email": "b@x.com"}),
        ),
        patch.object(bridge, "_map_odoo_user_by_email", AsyncMock(return_value=None)),
        patch.object(bridge, "_jaios_opportunity_url", return_value="https://jaios.justech.do/dgcp/1"),
    ):
        vals = await bridge._crm_vals(
            MagicMock(),
            opp,
            existing_lead={
                "x_justech_jaios_user_id": str(uid_a),
                "x_justech_jaios_user_name": "User A",
                "x_justech_jaios_user_email": "a@x.com",
            },
        )

    assert vals["x_justech_jaios_user_id"] == str(uid_a)
    assert vals["x_justech_jaios_user_name"] == "User A"
    assert vals["x_justech_jaios_owner_id"] == str(uid_b)
    assert vals["x_justech_jaios_owner_name"] == "User B"
    assert set(_INITIATOR_PAYLOAD_KEYS)


@pytest.mark.asyncio
async def test_owner_uses_responsible_user_id():
    actor = uuid.uuid4()
    owner = uuid.uuid4()
    bridge = DGCPOdooCrmBridge(db=AsyncMock(), tenant_id=uuid.uuid4(), user_id=actor)
    opp = _opp(full_info={"responsible_user_id": str(owner)})
    owner_user = SimpleNamespace(id=owner, full_name="Owner B", email="owner@x.com")
    with patch.object(bridge, "_load_user", AsyncMock(return_value=owner_user)):
        ident = await bridge._owner_identity(opp)
    assert ident["id"] == str(owner)
    assert ident["name"] == "Owner B"


@pytest.mark.asyncio
async def test_rpe_rejects_non_numeric():
    bridge = DGCPOdooCrmBridge(db=AsyncMock(), tenant_id=uuid.uuid4(), user_id=uuid.uuid4())
    # nested transaction path — force return None when query fails / non-numeric
    with patch.object(bridge.db, "begin_nested", side_effect=Exception("skip")):
        assert await bridge._rpe_for_company("just_office") is None
