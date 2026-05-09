"""Refresh token blacklist — Redis primary, in-memory fallback.

Adım 5: Redis'e migrate edildi. Multi-worker ve container-restart safe.
Redis down olursa graceful → in-memory dict devreye girer (kullanıcı tercihi).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.core.redis_client import redis_client

logger = get_logger(__name__)

BLACKLIST_KEY_PREFIX = "marketlens:blacklist"

# In-memory fallback (Redis down olduğunda devreye girer)
_fallback: dict[str, datetime] = {}
_fallback_lock = asyncio.Lock()


def _redis_key(jti: str) -> str:
    return f"{BLACKLIST_KEY_PREFIX}:{jti}"


async def add(jti: str, expires_at: datetime) -> None:
    """jti'yi blacklist'e ekle. Redis fail → in-memory fallback."""
    now = datetime.now(timezone.utc)
    ttl_seconds = max(1, int((expires_at - now).total_seconds()))

    try:
        await redis_client.setex(_redis_key(jti), ttl_seconds, "1")
        return
    except Exception as e:
        logger.warning(
            "redis_blacklist_add_failed_using_memory",
            jti=jti,
            error=str(e),
        )

    async with _fallback_lock:
        _fallback[jti] = expires_at


async def is_revoked(jti: str) -> bool:
    """jti revoke edilmiş mi? Redis fail → in-memory fallback."""
    try:
        return bool(await redis_client.exists(_redis_key(jti)))
    except Exception as e:
        logger.warning(
            "redis_blacklist_check_failed_using_memory",
            jti=jti,
            error=str(e),
        )

    async with _fallback_lock:
        # Lazy cleanup — exp'ı geçmiş kayıtları sil
        now = datetime.now(timezone.utc)
        expired_keys = [k for k, exp in _fallback.items() if exp < now]
        for k in expired_keys:
            del _fallback[k]
        return jti in _fallback


async def clear() -> None:
    """Test/debug için tüm blacklist'i temizle (Redis + in-memory)."""
    try:
        async for key in redis_client.scan_iter(match=f"{BLACKLIST_KEY_PREFIX}:*"):
            await redis_client.delete(key)
    except Exception as e:
        logger.warning("redis_blacklist_clear_failed", error=str(e))

    async with _fallback_lock:
        _fallback.clear()


async def size() -> int:
    """Mevcut entry sayısı (debug için, sadece Redis)."""
    try:
        count = 0
        async for _ in redis_client.scan_iter(match=f"{BLACKLIST_KEY_PREFIX}:*"):
            count += 1
        return count
    except Exception:
        async with _fallback_lock:
            return len(_fallback)
