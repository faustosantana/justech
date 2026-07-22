"""Distributed lock for lottery sync (Redis with in-memory fallback for tests)."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from app.config import settings


@dataclass
class SyncLockHandle:
    key: str
    token: str
    ttl_seconds: int


_MEMORY_LOCKS: dict[str, tuple[str, float]] = {}


class SyncLockError(RuntimeError):
    pass


async def acquire_sync_lock(key: str, *, ttl_seconds: int | None = None) -> SyncLockHandle:
    ttl = ttl_seconds or settings.lottery_sync_lock_ttl_seconds
    token = secrets.token_urlsafe(16)
    try:
        from app.core.redis_client import get_redis

        r = await get_redis()
        ok = await r.set(key, token, nx=True, ex=ttl)
        if not ok:
            raise SyncLockError(f"Lock ocupado: {key}")
        return SyncLockHandle(key=key, token=token, ttl_seconds=ttl)
    except SyncLockError:
        raise
    except Exception:
        # Fallback memoria (tests / redis down en local)
        now = time.time()
        existing = _MEMORY_LOCKS.get(key)
        if existing and existing[1] > now and existing[0] != token:
            raise SyncLockError(f"Lock ocupado: {key}")
        _MEMORY_LOCKS[key] = (token, now + ttl)
        return SyncLockHandle(key=key, token=token, ttl_seconds=ttl)


async def heartbeat_sync_lock(handle: SyncLockHandle) -> None:
    try:
        from app.core.redis_client import get_redis

        r = await get_redis()
        cur = await r.get(handle.key)
        if cur != handle.token:
            raise SyncLockError("Lock ajeno o expirado")
        await r.expire(handle.key, handle.ttl_seconds)
    except SyncLockError:
        raise
    except Exception:
        now = time.time()
        existing = _MEMORY_LOCKS.get(handle.key)
        if not existing or existing[0] != handle.token:
            raise SyncLockError("Lock ajeno o expirado")
        _MEMORY_LOCKS[handle.key] = (handle.token, now + handle.ttl_seconds)


async def release_sync_lock(handle: SyncLockHandle) -> None:
    try:
        from app.core.redis_client import get_redis

        r = await get_redis()
        cur = await r.get(handle.key)
        if cur == handle.token:
            await r.delete(handle.key)
    except Exception:
        existing = _MEMORY_LOCKS.get(handle.key)
        if existing and existing[0] == handle.token:
            _MEMORY_LOCKS.pop(handle.key, None)
