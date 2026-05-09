"""Refresh blacklist Redis primary + in-memory fallback testleri."""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import pytest
from pytest_mock import MockerFixture

from app.core.redis_client import redis_client
from app.services import refresh_blacklist


@pytest.fixture(autouse=True)
async def _clear_blacklist() -> AsyncIterator[None]:
    await refresh_blacklist.clear()
    yield
    await refresh_blacklist.clear()


async def test_redis_blacklist_add_and_check() -> None:
    jti = "test-jti-redis-1"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    assert await refresh_blacklist.is_revoked(jti) is False
    await refresh_blacklist.add(jti, expires_at)
    assert await refresh_blacklist.is_revoked(jti) is True


async def test_redis_blacklist_persists_in_redis() -> None:
    """Redis'e gerçekten yazıldığını doğrula (in-memory fallback değil)."""
    jti = "test-jti-redis-2"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    await refresh_blacklist.add(jti, expires_at)

    redis_value = await redis_client.get(f"marketlens:blacklist:{jti}")
    assert redis_value == "1"

    # TTL set edilmiş olmalı
    ttl = await redis_client.ttl(f"marketlens:blacklist:{jti}")
    assert 0 < ttl <= 5 * 60


async def test_fallback_when_redis_unavailable(mocker: MockerFixture) -> None:
    """Redis exception fırlatınca in-memory dict'e düşer."""
    mocker.patch.object(
        redis_client, "setex", side_effect=Exception("redis down")
    )
    mocker.patch.object(
        redis_client, "exists", side_effect=Exception("redis down")
    )

    jti = "test-jti-fallback"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    # add → in-memory'ye yazılır
    await refresh_blacklist.add(jti, expires_at)
    # is_revoked → in-memory'den okur
    assert await refresh_blacklist.is_revoked(jti) is True


async def test_unknown_jti_not_revoked() -> None:
    assert await refresh_blacklist.is_revoked("never-added-jti") is False
