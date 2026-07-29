"""In-process cache for active Studio compiled prompt."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheEntry:
    application: str
    version_id: str
    body: str
    compiled_prompt_hash: str
    semantic_version: str
    expires_at: float
    meta: dict[str, Any]


_lock = threading.Lock()
_ENTRY: _CacheEntry | None = None


def cache_get(application: str) -> _CacheEntry | None:
    global _ENTRY
    with _lock:
        if _ENTRY is None:
            return None
        if _ENTRY.application != application:
            return None
        if time.time() >= _ENTRY.expires_at:
            _ENTRY = None
            return None
        return _ENTRY


def cache_set(
    *,
    application: str,
    version_id: str,
    body: str,
    compiled_prompt_hash: str,
    semantic_version: str,
    ttl_seconds: int,
    meta: dict[str, Any] | None = None,
) -> None:
    global _ENTRY
    with _lock:
        _ENTRY = _CacheEntry(
            application=application,
            version_id=str(version_id),
            body=body,
            compiled_prompt_hash=compiled_prompt_hash,
            semantic_version=semantic_version,
            expires_at=time.time() + max(1, int(ttl_seconds)),
            meta=dict(meta or {}),
        )


def cache_invalidate(application: str | None = None) -> None:
    global _ENTRY
    with _lock:
        if application is None or (_ENTRY and _ENTRY.application == application):
            _ENTRY = None
