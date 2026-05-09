"""Redis cache decorator + helper.

Statik TTL için `@redis_cache(...)` decorator.
Dinamik TTL için `cached_call(key, ttl, fetch_fn)` helper.

Redis down olursa: graceful — cache atlanır, fetch_fn doğrudan çalışır.
JSON serialization: `default=str` (Decimal/datetime → string).
"""
from __future__ import annotations

import functools
import inspect
import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.logging import get_logger
from app.core.redis_client import redis_client

logger = get_logger(__name__)

CACHE_KEY_PREFIX = "marketlens"


def _full_key(key: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{key}"


async def cached_call(
    key: str,
    ttl: int,
    fetch_fn: Callable[[], Awaitable[Any]],
) -> Any:
    """Manuel cache helper. Dinamik TTL gereken durumlar için.

    `key`: prefix olmadan (örn. "klines:BTCUSDT:4H:500"). Otomatik prefix eklenir.
    Redis down → fetch_fn doğrudan çalışır.
    """
    fk = _full_key(key)

    try:
        cached = await redis_client.get(fk)
        if cached is not None:
            return json.loads(cached)
    except Exception as e:
        logger.warning("cache_read_failed", key=fk, error=str(e))

    result = await fetch_fn()

    try:
        await redis_client.set(fk, json.dumps(result, default=str), ex=ttl)
    except Exception as e:
        logger.warning("cache_write_failed", key=fk, error=str(e))

    return result


def redis_cache(key_template: str, ttl: int) -> Callable:
    """Statik TTL için decorator.

    `key_template` fonksiyon kwargs ile fill edilir; 'self' atılır.

    Örnek:
        @redis_cache("cg:global", ttl=300)
        async def get_global(self) -> dict: ...

        @redis_cache("klines:{symbol}:{tf}", ttl=60)
        async def get_klines(self, symbol: str, tf: str): ...
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            template_kwargs = {
                k: v for k, v in bound.arguments.items() if k != "self"
            }
            key = _full_key(key_template.format(**template_kwargs))

            try:
                cached = await redis_client.get(key)
                if cached is not None:
                    return json.loads(cached)
            except Exception as e:
                logger.warning("cache_read_failed", key=key, error=str(e))

            result = await func(*args, **kwargs)

            try:
                await redis_client.set(key, json.dumps(result, default=str), ex=ttl)
            except Exception as e:
                logger.warning("cache_write_failed", key=key, error=str(e))

            return result

        return wrapper

    return decorator
