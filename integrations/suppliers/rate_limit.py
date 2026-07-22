"""Rate limit simple por clave (tenant + proveedor)."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class SupplierRateLimiter:
    def __init__(self, max_calls: int = 12, period_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.period = period_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, key: str) -> None:
        lock = self._locks[key]
        async with lock:
            now = time.monotonic()
            q = self._events[key]
            while q and now - q[0] > self.period:
                q.popleft()
            if len(q) >= self.max_calls:
                wait = self.period - (now - q[0]) + 0.05
                await asyncio.sleep(max(wait, 0.1))
                return await self.acquire(key)
            q.append(time.monotonic())
