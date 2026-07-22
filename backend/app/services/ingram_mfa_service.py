"""Orquestación MFA manual Ingram CEP."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ingram_config_resolver import resolve_ingram_config
from app.services.ingram_session_service import IngramSessionService
from integrations.suppliers import ingram_okta

MFA_PENDING_MAX_AGE_SEC = 180


def _pending_fresh(pending: dict[str, Any] | None) -> bool:
    if not pending:
        return False
    created = pending.get("created_at")
    if not created:
        return True
    try:
        ts = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        return (datetime.now(UTC) - ts).total_seconds() < MFA_PENDING_MAX_AGE_SEC
    except ValueError:
        return False


class IngramMfaService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.sessions = IngramSessionService()

    async def start_mfa(self) -> dict[str, Any]:
        cfg = await resolve_ingram_config(self.db, self.tenant_id)
        if not cfg.username or not cfg.password:
            return {"ok": False, "status": "not_configured", "message": "Configure usuario y contraseña Ingram"}

        payload = await ingram_okta.start_auth(cfg.username, cfg.password)
        status = payload.get("status")
        if status == "SUCCESS" and payload.get("sessionToken"):
            cookies = await ingram_okta.establish_portal_cookies(
                payload["sessionToken"],
                redirect_url=cfg.portal_url.rstrip("/"),
            )
            session = await self.sessions.save_session(
                self.tenant_id,
                cookies=cookies,
                username=cfg.username,
                session_token=payload.get("sessionToken", ""),
            )
            await self.sessions.clear_mfa_pending(self.tenant_id)
            return {
                "ok": True,
                "status": "connected",
                "message": "Sesión Ingram activa (sin MFA)",
                "expires_at": session.get("expires_at"),
            }

        if status != "MFA_REQUIRED":
            return {
                "ok": False,
                "status": str(status or "unknown"),
                "message": "Respuesta inesperada de Ingram al iniciar sesión",
            }

        factors = payload.get("_embedded", {}).get("factors", [])
        factor = ingram_okta.pick_totp_factor(factors)
        if not factor:
            return {"ok": False, "status": "no_factor", "message": "No hay factor MFA disponible"}

        await self.sessions.save_mfa_pending(
            self.tenant_id,
            state_token=payload["stateToken"],
            factor_id=factor["id"],
            factor_type=factor.get("factorType", "totp"),
        )
        return {
            "ok": True,
            "status": "mfa_required",
            "message": "Ingrese el código de Google/Microsoft Authenticator",
            "factor_type": factor.get("factorType"),
            "provider": factor.get("provider"),
        }

    async def _ensure_mfa_pending(self, cfg) -> dict[str, Any]:
        pending = await self.sessions.get_mfa_pending(self.tenant_id)
        if _pending_fresh(pending):
            return {"ok": True, "status": "mfa_required", "message": "Desafío MFA activo"}

        await self.sessions.clear_mfa_pending(self.tenant_id)
        return await self.start_mfa()

    async def verify_mfa(self, pass_code: str) -> dict[str, Any]:
        cfg = await resolve_ingram_config(self.db, self.tenant_id)
        ensured = await self._ensure_mfa_pending(cfg)
        if ensured.get("status") == "connected":
            return ensured
        if not ensured.get("ok"):
            return ensured

        pending = await self.sessions.get_mfa_pending(self.tenant_id)
        if not pending:
            return {"ok": False, "status": "error", "message": "No se pudo iniciar desafío MFA"}

        try:
            result = await ingram_okta.verify_mfa_code(
                state_token=pending["state_token"],
                factor_id=pending["factor_id"],
                pass_code=pass_code.strip(),
            )
        except httpx.HTTPStatusError:
            await self.sessions.clear_mfa_pending(self.tenant_id)
            await self.start_mfa()
            return {
                "ok": False,
                "status": "invalid_code",
                "message": "Código incorrecto o expirado. Abra Authenticator, use el código nuevo y pulse Conectar.",
                "mfa_pending": True,
            }

        if result.get("status") != "SUCCESS":
            return {
                "ok": False,
                "status": result.get("status", "failed"),
                "message": "Código MFA incorrecto o expirado — solicite uno nuevo",
            }

        session_token = result.get("sessionToken")
        if not session_token:
            return {"ok": False, "status": "error", "message": "Ingram no devolvió sessionToken"}

        portal_warning: str | None = None
        try:
            cookies = await ingram_okta.establish_portal_cookies(
                session_token,
                redirect_url=cfg.portal_url.rstrip("/"),
            )
        except httpx.HTTPError as exc:
            cookies = []
            portal_warning = f"Sesión MFA OK; portal CEP no alcanzable desde el servidor ({type(exc).__name__})"

        session = await self.sessions.save_session(
            self.tenant_id,
            cookies=cookies,
            username=cfg.username,
            session_token=session_token,
        )
        await self.sessions.clear_mfa_pending(self.tenant_id)
        return {
            "ok": True,
            "status": "connected",
            "message": portal_warning or "Sesión Ingram conectada",
            "expires_at": session.get("expires_at"),
            "cookie_count": len(cookies),
            "session_active": True,
        }

    async def disconnect(self) -> dict[str, Any]:
        await self.sessions.clear_session(self.tenant_id)
        await self.sessions.clear_mfa_pending(self.tenant_id)
        return {"ok": True, "status": "disconnected", "message": "Sesión Ingram cerrada"}

    async def get_session_cookies(self) -> list[dict[str, str]] | None:
        session = await self.sessions.get_session(self.tenant_id)
        if not session:
            return None
        return session.get("cookies") or []
