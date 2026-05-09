"""Smoke tests for /health endpoint + RequestIDMiddleware."""
from __future__ import annotations

import re

from httpx import AsyncClient

UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "marketlens-backend"
    assert "version" in body
    assert "environment" in body


async def test_health_request_id_echoed_when_provided(client: AsyncClient) -> None:
    """X-Request-ID header verirsek, response'ta aynı id dönmeli."""
    test_id = "smoke-test-abc-123"
    response = await client.get("/health", headers={"X-Request-ID": test_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == test_id


async def test_health_request_id_generated_when_absent(client: AsyncClient) -> None:
    """Header yoksa middleware uuid4 üretmeli."""
    response = await client.get("/health")
    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id is not None
    assert UUID4_RE.match(request_id), f"Beklenmeyen format: {request_id}"


async def test_health_each_request_gets_unique_id(client: AsyncClient) -> None:
    """Auto-generated ID'ler request başına farklı olmalı."""
    r1 = await client.get("/health")
    r2 = await client.get("/health")
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]
