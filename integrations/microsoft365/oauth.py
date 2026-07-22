"""OAuth 2.0 Microsoft Entra ID — authorization code + refresh."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from integrations.microsoft365.config import DEFAULT_READ_SCOPES, M365Config
from integrations.microsoft365.schemas import M365OAuthTokens


class M365OAuthError(Exception):
    pass


def authorization_url(config: M365Config, *, state: str, scopes: tuple[str, ...] | None = None) -> str:
    if not config.is_configured():
        raise M365OAuthError("Microsoft 365 no configurado (M365_TENANT_ID, CLIENT_ID, CLIENT_SECRET)")
    scope_list = scopes or DEFAULT_READ_SCOPES
    params = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": config.redirect_uri,
        "response_mode": "query",
        "scope": " ".join(scope_list),
        "state": state,
    }
    base = f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/authorize"
    return f"{base}?{urlencode(params)}"


async def exchange_code(config: M365Config, code: str) -> M365OAuthTokens:
    token_url = f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "code": code,
        "redirect_uri": config.redirect_uri,
        "grant_type": "authorization_code",
        "scope": " ".join(DEFAULT_READ_SCOPES),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code >= 400:
            raise M365OAuthError(f"Error token OAuth: {resp.text[:500]}")
        payload = resp.json()
    expires_at = None
    if "expires_in" in payload:
        expires_at = datetime.now(UTC) + timedelta(seconds=int(payload["expires_in"]))
    scopes = (payload.get("scope") or "").split()
    return M365OAuthTokens(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        expires_at=expires_at,
        scopes=scopes,
    )


async def refresh_tokens(config: M365Config, refresh_token: str) -> M365OAuthTokens:
    token_url = f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(DEFAULT_READ_SCOPES),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code >= 400:
            raise M365OAuthError(f"Error refresh token: {resp.text[:500]}")
        payload = resp.json()
    expires_at = None
    if "expires_in" in payload:
        expires_at = datetime.now(UTC) + timedelta(seconds=int(payload["expires_in"]))
    return M365OAuthTokens(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token") or refresh_token,
        expires_at=expires_at,
        scopes=(payload.get("scope") or "").split(),
    )
