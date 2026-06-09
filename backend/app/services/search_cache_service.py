"""Search Cache Layer — Redis por tenant (Fase 6.5)."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from app.config import settings
from app.core.redis_client import get_redis

META_PREFIX = "jaios:search:cache:meta:"
CACHE_PREFIX = "jaios:search:cache:"
ODOO_PREFIX = "jaios:search:odoo:"
DGCP_PREFIX = "jaios:search:dgcp:"


class SearchCacheService:
    def _stable_hash(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    async def get_tenant_version(self, tenant_id: uuid.UUID) -> int:
        if not settings.search_cache_enabled:
            return 0
        redis = await get_redis()
        val = await redis.get(f"{META_PREFIX}{tenant_id}")
        return int(val) if val else 0

    async def invalidate_tenant(self, tenant_id: uuid.UUID) -> None:
        if not settings.search_cache_enabled:
            return
        redis = await get_redis()
        await redis.incr(f"{META_PREFIX}{tenant_id}")

    async def get_response(
        self,
        tenant_id: uuid.UUID,
        *,
        channel: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not settings.search_cache_enabled:
            return None
        version = await self.get_tenant_version(tenant_id)
        key = f"{CACHE_PREFIX}{tenant_id}:{version}:{channel}:{self._stable_hash(params)}"
        redis = await get_redis()
        raw = await redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def set_response(
        self,
        tenant_id: uuid.UUID,
        *,
        channel: str,
        params: dict[str, Any],
        payload: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        if not settings.search_cache_enabled:
            return
        ttl = ttl_seconds or (
            settings.search_cache_assistant_ttl_seconds
            if channel == "assistant"
            else settings.search_cache_ttl_seconds
        )
        version = await self.get_tenant_version(tenant_id)
        key = f"{CACHE_PREFIX}{tenant_id}:{version}:{channel}:{self._stable_hash(params)}"
        redis = await get_redis()
        await redis.set(key, json.dumps(payload, ensure_ascii=False, default=str), ex=ttl)

    async def get_slice(
        self,
        tenant_id: uuid.UUID,
        *,
        slice_key: str,
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not settings.search_cache_enabled:
            return None
        version = await self.get_tenant_version(tenant_id)
        prefix = ODOO_PREFIX if slice_key == "odoo" else DGCP_PREFIX if slice_key == "dgcp" else CACHE_PREFIX
        key = f"{prefix}{tenant_id}:{version}:{slice_key}:{self._stable_hash(params)}"
        redis = await get_redis()
        raw = await redis.get(key)
        return json.loads(raw) if raw else None

    async def set_slice(
        self,
        tenant_id: uuid.UUID,
        *,
        slice_key: str,
        params: dict[str, Any],
        payload: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        if not settings.search_cache_enabled:
            return
        version = await self.get_tenant_version(tenant_id)
        prefix = ODOO_PREFIX if slice_key == "odoo" else DGCP_PREFIX if slice_key == "dgcp" else CACHE_PREFIX
        key = f"{prefix}{tenant_id}:{version}:{slice_key}:{self._stable_hash(params)}"
        redis = await get_redis()
        await redis.set(key, json.dumps(payload, ensure_ascii=False, default=str), ex=ttl_seconds)
