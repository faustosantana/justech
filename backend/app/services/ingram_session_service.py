"""Sesión Ingram CEP (MFA + cookies) en Redis por tenant."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.redis_client import get_redis

SESSION_PREFIX = "jaios:ingram:session:"
MFA_PREFIX = "jaios:ingram:mfa:"
SESSION_TTL_SECONDS = 4 * 3600
MFA_TTL_SECONDS = 5 * 60


class IngramSessionService:
    def _session_key(self, tenant_id: uuid.UUID) -> str:
        return f"{SESSION_PREFIX}{tenant_id}"

    def _mfa_key(self, tenant_id: uuid.UUID) -> str:
        return f"{MFA_PREFIX}{tenant_id}"

    async def get_session(self, tenant_id: uuid.UUID) -> dict[str, Any] | None:
        redis = await get_redis()
        raw = await redis.get(self._session_key(tenant_id))
        if not raw:
            return None
        data = json.loads(raw)
        if data.get("expires_at", 0) < time.time():
            await self.clear_session(tenant_id)
            return None
        return data

    async def save_session(
        self,
        tenant_id: uuid.UUID,
        *,
        cookies: list[dict[str, str]],
        username: str,
        session_token: str = "",
        ttl_seconds: int = SESSION_TTL_SECONDS,
    ) -> dict[str, Any]:
        payload = {
            "username": username,
            "cookies": cookies,
            "session_token": session_token,
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": time.time() + ttl_seconds,
        }
        redis = await get_redis()
        await redis.set(
            self._session_key(tenant_id),
            json.dumps(payload, ensure_ascii=False),
            ex=ttl_seconds,
        )
        return payload

    async def clear_session(self, tenant_id: uuid.UUID) -> None:
        redis = await get_redis()
        await redis.delete(self._session_key(tenant_id))

    async def get_mfa_pending(self, tenant_id: uuid.UUID) -> dict[str, Any] | None:
        redis = await get_redis()
        raw = await redis.get(self._mfa_key(tenant_id))
        return json.loads(raw) if raw else None

    async def save_mfa_pending(
        self,
        tenant_id: uuid.UUID,
        *,
        state_token: str,
        factor_id: str,
        factor_type: str,
        ttl_seconds: int = MFA_TTL_SECONDS,
    ) -> None:
        redis = await get_redis()
        await redis.set(
            self._mfa_key(tenant_id),
            json.dumps(
                {
                    "state_token": state_token,
                    "factor_id": factor_id,
                    "factor_type": factor_type,
                    "created_at": datetime.now(UTC).isoformat(),
                },
                ensure_ascii=False,
            ),
            ex=ttl_seconds,
        )

    async def clear_mfa_pending(self, tenant_id: uuid.UUID) -> None:
        redis = await get_redis()
        await redis.delete(self._mfa_key(tenant_id))

    async def session_status(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        session = await self.get_session(tenant_id)
        pending = await self.get_mfa_pending(tenant_id)
        if session:
            expires = datetime.fromtimestamp(session["expires_at"], tz=UTC)
            return {
                "session_active": True,
                "mfa_pending": False,
                "expires_at": expires.isoformat(),
                "username": session.get("username"),
            }
        if pending:
            return {
                "session_active": False,
                "mfa_pending": True,
                "factor_type": pending.get("factor_type"),
            }
        return {"session_active": False, "mfa_pending": False}
