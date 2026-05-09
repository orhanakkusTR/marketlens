"""Pytest paylaşılan fixture'lar — async HTTP client ASGI üzerinden."""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """In-process async HTTP client (gerçek server başlatmaz, ASGI app'e direkt vurur).

    `raise_app_exceptions=False`: Starlette'in ServerErrorMiddleware'i unhandled
    Exception'lar için 500 response gönderir AMA exception'ı yine raise eder
    (server logging için). Test ortamında bu raise'i bastırıp response'u test ediyoruz.
    """
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
