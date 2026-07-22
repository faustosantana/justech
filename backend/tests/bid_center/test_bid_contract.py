"""Unit tests for Bid contract + Bid Center client (mocked)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.bid_contract import BidOpportunityV1, InterestRequest, compute_content_hash
from app.services.bid_center.odoo_client import OdooBidCenterClient


def test_contract_roundtrip():
    payload = {
        "schema_version": "1.0.0",
        "source_system": "jaios",
        "external_id": "abc",
        "title": "T",
        "institution_name": "Org",
        "compatibility_score": 50,
    }
    m = BidOpportunityV1.model_validate(payload)
    assert m.jaios_tender_id == "abc"
    assert m.content_hash.startswith("sha256:")
    assert compute_content_hash(m.model_dump()) == m.content_hash


def test_contract_rejects_bad_schema():
    with pytest.raises(Exception):
        BidOpportunityV1.model_validate({
            "schema_version": "2.0.0",
            "source_system": "jaios",
            "external_id": "x",
            "title": "t",
            "institution_name": "i",
        })


def test_client_disabled():
    with patch("app.services.bid_center.odoo_client.settings") as s:
        s.bid_center_enabled = False
        s.bid_center_url = ""
        s.bid_center_api_key = ""
        s.bid_center_hmac_secret = ""
        s.bid_center_timeout = 5
        c = OdooBidCenterClient()
        assert c.health()["status"] == "disabled"
        with pytest.raises(RuntimeError):
            c.upsert_opportunity({"x": 1})


def test_client_interest_headers():
    with patch("app.services.bid_center.odoo_client.settings") as s:
        s.bid_center_enabled = True
        s.bid_center_url = "http://odoo.test"
        s.bid_center_api_key = "secret-key"
        s.bid_center_hmac_secret = "hmac"
        s.bid_center_timeout = 5
        c = OdooBidCenterClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"ok":true,"odoo_tender_id":9,"idempotent":false}'
        mock_resp.json.return_value = {"ok": True, "odoo_tender_id": 9, "idempotent": False}
        with patch("httpx.Client") as client_cls:
            client = MagicMock()
            client_cls.return_value.__enter__.return_value = client
            client.request.return_value = mock_resp
            out = c.show_interest("tid-1", idempotency_key="k1", body={"origin": "jaios"})
            assert out["odoo_tender_id"] == 9
            args, kwargs = client.request.call_args
            assert args[0] == "POST"
            assert "Idempotency-Key" in kwargs["headers"]
            assert kwargs["headers"]["X-Api-Key"] == "secret-key"
            assert "X-Signature" in kwargs["headers"]


def test_interest_request_model():
    r = InterestRequest(idempotency_key="abc")
    assert r.origin == "jaios"
