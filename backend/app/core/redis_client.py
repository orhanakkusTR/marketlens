"""Async Redis client singleton.

Lifespan tarafından `close_redis()` çağrılır.
"""
from __future__ import annotations

import redis.asyncio as redis_async

from app.core.config import settings

# Modül seviyesi singleton. Pool ilk istekte oluşur.
redis_client: redis_async.Redis = redis_async.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    health_check_interval=30,
    socket_keepalive=True,
)


async def close_redis() -> None:
    """Lifespan shutdown handler."""
    await redis_client.aclose()
