"""AbstractDataClient retry + breaker testleri."""
from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from app.core.circuit_breaker import CircuitBreakerError
from app.data.base import AbstractDataClient


class _FakeClient(AbstractDataClient):
    """Test için minimum subclass."""


async def test_request_succeeds_first_try(mocker: MockerFixture) -> None:
    client = _FakeClient(base_url="http://test")
    mock_response = httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json={"ok": True})
    request_mock = mocker.patch.object(
        client._http, "request", return_value=mock_response
    )

    response = await client.request("GET", "/foo")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert request_mock.call_count == 1

    await client.close()


async def test_request_retries_on_transport_error(mocker: MockerFixture) -> None:
    client = _FakeClient(base_url="http://test")
    success = httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json={"ok": True})

    request_mock = mocker.patch.object(
        client._http,
        "request",
        side_effect=[
            httpx.ConnectError("first"),
            httpx.ConnectError("second"),
            success,
        ],
    )

    response = await client.request("GET", "/foo")
    assert response.status_code == 200
    assert request_mock.call_count == 3  # 2 hata + 1 başarı

    await client.close()


async def test_request_no_retry_on_4xx(mocker: MockerFixture) -> None:
    client = _FakeClient(base_url="http://test")
    error_response = httpx.Response(request=httpx.Request("GET", "http://test"), status_code=400, json={"error": "bad request"})

    request_mock = mocker.patch.object(
        client._http, "request", return_value=error_response
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.request("GET", "/foo")

    assert request_mock.call_count == 1  # 4xx → retry yok

    await client.close()


async def test_request_retries_on_5xx(mocker: MockerFixture) -> None:
    client = _FakeClient(base_url="http://test")
    error_response = httpx.Response(request=httpx.Request("GET", "http://test"), status_code=503, text="unavailable")
    success = httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json={"ok": True})

    request_mock = mocker.patch.object(
        client._http, "request", side_effect=[error_response, success]
    )

    response = await client.request("GET", "/foo")
    assert response.status_code == 200
    assert request_mock.call_count == 2

    await client.close()


async def test_breaker_eventually_opens(mocker: MockerFixture) -> None:
    """Sürekli hata atılınca pybreaker 5 fail sonrası CircuitBreakerError fırlatmalı."""
    client = _FakeClient(base_url="http://test")
    mocker.patch.object(
        client._http, "request", side_effect=httpx.ConnectError("net down")
    )

    breaker_opened = False
    for _ in range(10):
        try:
            await client.request("GET", "/foo")
        except CircuitBreakerError:
            breaker_opened = True
            break
        except httpx.ConnectError:
            pass

    assert breaker_opened, "Breaker açılmadı (5+ fail beklenirdi)"

    await client.close()
