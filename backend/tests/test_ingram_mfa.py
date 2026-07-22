"""Tests MFA manual Ingram."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.ingram_mfa_service import IngramMfaService


@pytest.mark.asyncio
async def test_start_mfa_requires_credentials():
    svc = IngramMfaService(db=AsyncMock(), tenant_id="00000000-0000-0000-0000-000000000001")
    with patch(
        "app.services.ingram_mfa_service.resolve_ingram_config",
        AsyncMock(return_value=type("C", (), {"username": "", "password": ""})()),
    ):
        result = await svc.start_mfa()
    assert result["ok"] is False
    assert result["status"] == "not_configured"


@pytest.mark.asyncio
async def test_verify_mfa_success():
    svc = IngramMfaService(db=AsyncMock(), tenant_id="00000000-0000-0000-0000-000000000001")
    cfg = type(
        "C",
        (),
        {"username": "u@test.do", "password": "secret", "portal_url": "https://mi.ingrammicro.com/cep/app"},
    )()
    pending = {"state_token": "st", "factor_id": "fid", "factor_type": "token:software:totp"}

    with patch("app.services.ingram_mfa_service.resolve_ingram_config", AsyncMock(return_value=cfg)):
        with patch.object(svc.sessions, "get_mfa_pending", AsyncMock(return_value=pending)):
            with patch(
                "app.services.ingram_mfa_service.ingram_okta.verify_mfa_code",
                AsyncMock(return_value={"status": "SUCCESS", "sessionToken": "sess"}),
            ):
                with patch(
                    "app.services.ingram_mfa_service.ingram_okta.establish_portal_cookies",
                    AsyncMock(return_value=[{"name": "sid", "value": "abc"}]),
                ):
                    with patch.object(
                        svc.sessions,
                        "save_session",
                        AsyncMock(return_value={"expires_at": 9999999999.0}),
                    ):
                        with patch.object(svc.sessions, "clear_mfa_pending", AsyncMock()):
                            result = await svc.verify_mfa("123456")

    assert result["ok"] is True
    assert result["status"] == "connected"
