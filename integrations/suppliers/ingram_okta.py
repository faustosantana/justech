"""Autenticación Okta — portal CEP Ingram (mi.ingrammicro.com)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

OKTA_BASE = "https://myaccount.ingrammicro.com"
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; JAIOS/1.0; +https://justech.do)",
}


def pick_totp_factor(factors: list[dict]) -> dict | None:
    for factor in factors:
        if factor.get("factorType") == "token:software:totp":
            return factor
    return factors[0] if factors else None


async def start_auth(username: str, password: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30, headers=DEFAULT_HEADERS) as client:
        resp = await client.post(
            f"{OKTA_BASE}/api/v1/authn",
            json={"username": username, "password": password},
        )
        resp.raise_for_status()
        return resp.json()


async def verify_mfa_code(
    *,
    state_token: str,
    factor_id: str,
    pass_code: str,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30, headers=DEFAULT_HEADERS) as client:
        resp = await client.post(
            f"{OKTA_BASE}/api/v1/authn/factors/{factor_id}/verify",
            json={"stateToken": state_token, "passCode": pass_code.strip()},
        )
        resp.raise_for_status()
        return resp.json()


async def establish_portal_cookies(
    session_token: str,
    *,
    redirect_url: str = "https://mi.ingrammicro.com/cep/app",
) -> list[dict[str, str]]:
    """Intercambia sessionToken Okta por cookies (sin seguir redirect a mi.* — evita timeout VPS)."""
    url = (
        f"{OKTA_BASE}/login/sessionCookieRedirect"
        f"?token={quote(session_token, safe='')}"
        f"&redirectUrl={quote(redirect_url, safe='')}"
    )
    cookies_out: list[dict[str, str]] = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        await client.get(url, headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]})
        for cookie in client.cookies.jar:
            cookies_out.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain or "",
                    "path": cookie.path or "/",
                }
            )
    return cookies_out


def cookies_to_header(cookies: list[dict[str, str]]) -> str:
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies if c.get("name"))
