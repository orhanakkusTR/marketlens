"""Async-native Circuit Breaker.

pybreaker'ın `call_async` metodu tornado'ya bağımlı (tornado yüklü değil) ve
bilinen bir sorun. Bu basit, asyncio-first implementasyon onun yerini alır.

State machine:
    CLOSED → fail_max ardışık hata → OPEN
    OPEN → reset_timeout sonra → HALF_OPEN
    HALF_OPEN → 1 başarı → CLOSED, 1 hata → OPEN

Kullanım:
    breaker = AsyncCircuitBreaker(fail_max=5, reset_timeout=30, name="binance")
    result = await breaker.call(some_async_fn, arg1, arg2)
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, TypeVar


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Breaker open iken yapılan çağrıda fırlatılır."""


T = TypeVar("T")


class AsyncCircuitBreaker:
    """Async-native circuit breaker (pybreaker.tornado bağımsız)."""

    def __init__(
        self,
        fail_max: int = 5,
        reset_timeout: float = 30.0,
        name: str = "",
    ) -> None:
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.name = name
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def current_state(self) -> CircuitState:
        return self._state

    @property
    def fail_counter(self) -> int:
        return self._failure_count

    async def _check_state(self) -> None:
        """Çağrı yapmadan önce state'i kontrol et. OPEN ise hata fırlat."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                # Reset timeout doldu mu — half-open'a geç
                if (
                    self._opened_at is not None
                    and (time.monotonic() - self._opened_at) >= self.reset_timeout
                ):
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerError(
                        f"Circuit '{self.name}' is OPEN"
                    )

    async def _on_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            self._opened_at = None

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.fail_max:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    async def call(
        self,
        fn: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Korumalı async çağrı. Open ise CircuitBreakerError fırlatır."""
        await self._check_state()
        try:
            result = await fn(*args, **kwargs)
        except Exception:
            await self._on_failure()
            raise
        else:
            await self._on_success()
            return result

    def reset(self) -> None:
        """Manuel reset (test/admin için)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None
