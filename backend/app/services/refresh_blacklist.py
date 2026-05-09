"""In-memory refresh token blacklist (jti → expires_at).

Adım 4 geçici çözüm. Sınırlamaları:
- Tek worker'da çalışır. Multi-worker'da paylaşılmaz (her worker kendi dict'i).
- Container restart'ta sıfırlanır → tüm refresh tokenlar yine geçerli olur.

Adım 5'te Redis client gelince Redis-backed bir implementasyona geçilecek
(aynı arayüz: add, is_revoked, clear).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

_blacklist: dict[str, datetime] = {}
_lock = asyncio.Lock()


async def add(jti: str, expires_at: datetime) -> None:
    """jti'yi blacklist'e ekle. expires_at sadece lazy cleanup için."""
    async with _lock:
        _blacklist[jti] = expires_at


async def is_revoked(jti: str) -> bool:
    """jti revoke edilmiş mi? Lazy cleanup yapar."""
    async with _lock:
        now = datetime.now(timezone.utc)
        # Lazy cleanup — exp'ı geçmiş kayıtları sil
        expired_keys = [k for k, exp in _blacklist.items() if exp < now]
        for k in expired_keys:
            del _blacklist[k]
        return jti in _blacklist


async def clear() -> None:
    """Tüm blacklist'i temizle (sadece test/debug için)."""
    async with _lock:
        _blacklist.clear()


async def size() -> int:
    """Mevcut entry sayısı (debug için)."""
    async with _lock:
        return len(_blacklist)
