"""Cliente Redis async — una conexión por event loop."""

from __future__ import annotations

import asyncio

import redis.asyncio as redis

from app.config import settings

_clients: dict[asyncio.AbstractEventLoop, redis.Redis] = {}


async def get_redis() -> redis.Redis:
    loop = asyncio.get_running_loop()
    client = _clients.get(loop)
    if client is None:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        _clients[loop] = client
    return client


async def close_redis() -> None:
    loop = asyncio.get_running_loop()
    client = _clients.pop(loop, None)
    if client is not None:
        await client.aclose()
