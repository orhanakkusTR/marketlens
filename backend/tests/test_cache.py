"""Cache decorator + helper testleri."""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from pytest_mock import MockerFixture

from app.core.cache import cached_call, redis_cache
from app.core.redis_client import redis_client


@pytest.fixture(autouse=True)
async def _clear_test_cache_keys() -> AsyncIterator[None]:
    """Test öncesi/sonrası `marketlens:test:*` ve `marketlens:cache_test:*` siler."""
    patterns = ["marketlens:test:*", "marketlens:cache_test:*"]
    for pattern in patterns:
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
    yield
    for pattern in patterns:
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)


async def test_cached_call_miss_then_hit() -> None:
    call_count = 0

    async def fetcher() -> dict[str, str]:
        nonlocal call_count
        call_count += 1
        return {"data": "value"}

    # 1st: miss → fetcher çağrılır
    r1 = await cached_call("test:foo", ttl=10, fetch_fn=fetcher)
    assert r1 == {"data": "value"}
    assert call_count == 1

    # 2nd: hit → fetcher çağrılmaz
    r2 = await cached_call("test:foo", ttl=10, fetch_fn=fetcher)
    assert r2 == {"data": "value"}
    assert call_count == 1


async def test_cached_call_graceful_when_redis_down(mocker: MockerFixture) -> None:
    """Redis exception fırlatınca fetch_fn yine çalışmalı."""
    mocker.patch.object(
        redis_client, "get", side_effect=Exception("redis down")
    )
    mocker.patch.object(
        redis_client, "set", side_effect=Exception("redis down")
    )

    call_count = 0

    async def fetcher() -> int:
        nonlocal call_count
        call_count += 1
        return 42

    r = await cached_call("test:graceful", ttl=10, fetch_fn=fetcher)
    assert r == 42
    assert call_count == 1


async def test_redis_cache_decorator_hit() -> None:
    call_count = 0

    @redis_cache("cache_test:bar:{name}", ttl=10)
    async def get_value(name: str) -> dict[str, int]:
        nonlocal call_count
        call_count += 1
        return {"name": name, "value": 42}  # type: ignore[dict-item]

    r1 = await get_value(name="foo")
    r2 = await get_value(name="foo")

    assert r1 == r2
    assert call_count == 1  # 2. çağrı cache'den


async def test_redis_cache_different_keys_separate() -> None:
    call_count = 0

    @redis_cache("cache_test:bar:{n}", ttl=10)
    async def fn(n: int) -> int:
        nonlocal call_count
        call_count += 1
        return n * 2

    r1 = await fn(n=1)
    r2 = await fn(n=2)
    r3 = await fn(n=1)  # cache hit

    assert r1 == 2
    assert r2 == 4
    assert r3 == 2
    assert call_count == 2  # n=1 ve n=2 ayrı keyler


async def test_redis_cache_with_method_self_excluded() -> None:
    """Decorator method'larda 'self' parametresini key template'e dahil etmez."""

    class _T:
        def __init__(self) -> None:
            self.calls = 0

        @redis_cache("cache_test:obj:{x}", ttl=10)
        async def compute(self, x: int) -> int:
            self.calls += 1
            return x * 10

    obj = _T()
    r1 = await obj.compute(x=5)
    r2 = await obj.compute(x=5)
    assert r1 == r2 == 50
    assert obj.calls == 1
