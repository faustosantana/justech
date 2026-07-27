"""Research result cache — avoid repeating identical tool calls (Fase B)."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchCache:
    """In-process TTL cache for tool results within / across a research turn."""

    ttl_seconds: float = 120.0
    max_entries: int = 64
    _store: dict[str, tuple[float, Any]] = field(default_factory=dict)

    @staticmethod
    def make_key(tool: str, params: dict[str, Any] | None) -> str:
        payload = json.dumps(
            {"tool": tool, "params": params or {}},
            sort_keys=True,
            default=str,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def get(self, tool: str, params: dict[str, Any] | None) -> Any | None:
        key = self.make_key(tool, params)
        item = self._store.get(key)
        if not item:
            return None
        ts, value = item
        if (time.monotonic() - ts) > self.ttl_seconds:
            self._store.pop(key, None)
            return None
        return value

    def set(self, tool: str, params: dict[str, Any] | None, value: Any) -> None:
        if len(self._store) >= self.max_entries:
            # drop oldest
            oldest = min(self._store.items(), key=lambda kv: kv[1][0])[0]
            self._store.pop(oldest, None)
        self._store[self.make_key(tool, params)] = (time.monotonic(), value)

    def clear(self) -> None:
        self._store.clear()


# Shared soft cache for the process (safe: tool outputs are read-only historical)
_GLOBAL_RESEARCH_CACHE = ResearchCache()


def get_research_cache() -> ResearchCache:
    return _GLOBAL_RESEARCH_CACHE
