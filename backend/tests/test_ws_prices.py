"""WebSocket /ws/prices endpoint smoke testleri."""
from __future__ import annotations

import pytest


async def test_invalid_token_returns_none_from_authenticate() -> None:
    """Geçersiz token → None (WS close 4401 sebebi)."""
    from app.api.v1.ws import _authenticate_token

    result = await _authenticate_token("invalid.token.value")
    assert result is None


async def test_empty_token_returns_none() -> None:
    from app.api.v1.ws import _authenticate_token

    result = await _authenticate_token("")
    assert result is None


def test_close_codes_in_application_range() -> None:
    """WS application close codes 4000-4999 range içinde."""
    from app.api.v1.ws import WS_CLOSE_INVALID_MESSAGE, WS_CLOSE_UNAUTHORIZED

    assert 4000 <= WS_CLOSE_UNAUTHORIZED <= 4999
    assert 4000 <= WS_CLOSE_INVALID_MESSAGE <= 4999
