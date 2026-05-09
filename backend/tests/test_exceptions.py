"""Smoke tests for exception handling — standart format dönmeli."""
from __future__ import annotations

import pytest
from fastapi import APIRouter
from httpx import AsyncClient

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.main import app

# Test-only router — production route'ları kirletmesin diye `/__test` prefix'i.
_test_router = APIRouter(prefix="/__test", include_in_schema=False)


@_test_router.get("/raise/notfound")
async def _raise_notfound() -> None:
    raise NotFoundError("Sembol bulunamadı", details={"symbol": "FAKEUSDT"})


@_test_router.get("/raise/unauthorized")
async def _raise_unauthorized() -> None:
    raise UnauthorizedError()


@_test_router.get("/raise/forbidden")
async def _raise_forbidden() -> None:
    raise ForbiddenError()


@_test_router.get("/raise/conflict")
async def _raise_conflict() -> None:
    raise ConflictError()


@_test_router.get("/raise/validation")
async def _raise_validation() -> None:
    raise ValidationError("Tarih aralığı geçersiz")


@_test_router.get("/raise/unhandled")
async def _raise_unhandled() -> None:
    raise RuntimeError("simulated bug — pytest fixture")


# Modül yüklenirken router register edilir (test session için).
app.include_router(_test_router)


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_error_code"),
    [
        ("/__test/raise/notfound", 404, "not_found"),
        ("/__test/raise/unauthorized", 401, "unauthorized"),
        ("/__test/raise/forbidden", 403, "forbidden"),
        ("/__test/raise/conflict", 409, "conflict"),
        ("/__test/raise/validation", 422, "validation_error"),
    ],
)
async def test_marketlens_errors_return_standard_format(
    client: AsyncClient,
    path: str,
    expected_status: int,
    expected_error_code: str,
) -> None:
    response = await client.get(path)
    assert response.status_code == expected_status

    body = response.json()
    # Standart format key'leri
    assert set(body.keys()) >= {"error", "message", "details", "request_id"}
    assert body["error"] == expected_error_code
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["details"], dict)
    assert body["request_id"] is not None  # RequestIDMiddleware bunu garanti eder


async def test_notfound_includes_custom_details(client: AsyncClient) -> None:
    response = await client.get("/__test/raise/notfound")
    body = response.json()
    assert body["details"]["symbol"] == "FAKEUSDT"
    assert body["message"] == "Sembol bulunamadı"


async def test_unhandled_exception_returns_500_without_leak(client: AsyncClient) -> None:
    """Beklenmeyen exception 500 dönmeli + iç detay sızdırmamalı."""
    response = await client.get("/__test/raise/unhandled")
    assert response.status_code == 500

    body = response.json()
    assert body["error"] == "internal_error"
    # Stack/RuntimeError detayı response'a sızmamalı
    assert "RuntimeError" not in str(body)
    assert "simulated bug" not in str(body)


async def test_404_for_unknown_path_uses_standard_format(client: AsyncClient) -> None:
    """FastAPI'nin built-in 404'ü de aynı format dönmeli."""
    response = await client.get("/this/path/does/not/exist")
    assert response.status_code == 404

    body = response.json()
    assert set(body.keys()) >= {"error", "message", "details", "request_id"}
    assert body["error"] == "http_404"


async def test_request_id_in_error_response(client: AsyncClient) -> None:
    """Hata response'ında client'ın gönderdiği X-Request-ID görünmeli."""
    test_id = "exc-test-xyz-789"
    response = await client.get(
        "/__test/raise/notfound",
        headers={"X-Request-ID": test_id},
    )
    body = response.json()
    assert body["request_id"] == test_id
