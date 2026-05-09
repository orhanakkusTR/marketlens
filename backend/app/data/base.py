"""AbstractDataClient — httpx + tenacity retry + AsyncCircuitBreaker.

Retry: 3 deneme, exp backoff 1-2-4 sn.
- TransportError, RemoteProtocolError → retry
- HTTPStatusError 5xx → retry
- HTTPStatusError 4xx → no retry (kullanıcı hatası)
- CircuitBreakerError → no retry (breaker zaten açık)

Breaker: 5 hata sonrası açılır, 30 sn sonra yarı açık.
"""
from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.circuit_breaker import AsyncCircuitBreaker, CircuitBreakerError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Retry edilecek exception'ları belirle."""
    if isinstance(exc, CircuitBreakerError):
        return False  # breaker açık, retry boşa
    if isinstance(exc, (httpx.TransportError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


class AbstractDataClient:
    """Tüm external API client'larının base'i."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        self.breaker = AsyncCircuitBreaker(
            fail_max=5,
            reset_timeout=30.0,
            name=self.__class__.__name__,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _do_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        response = await self._http.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Retry + breaker korumalı HTTP request."""
        return await self.breaker.call(
            self._do_request, method, url, **kwargs
        )
