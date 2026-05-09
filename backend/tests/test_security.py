"""Smoke tests for security primitives — bcrypt + JWT (kid rotation dahil)."""
from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from jose import jwt as jose_jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    _build_token,
    _resolve_secret,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

# ─── Password hashing ───


def test_password_hash_and_verify_roundtrip() -> None:
    plain = "test_password_123!"
    hashed = hash_password(plain)
    assert hashed != plain
    # bcrypt hash format: $2b$<cost>$<salt+hash>
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_password_hash_unique_per_call() -> None:
    """bcrypt salt'lı — aynı şifre farklı hash üretmeli."""
    plain = "same_password"
    h1 = hash_password(plain)
    h2 = hash_password(plain)
    assert h1 != h2
    # ama her ikisi de doğrulanabilmeli
    assert verify_password(plain, h1)
    assert verify_password(plain, h2)


# ─── JWT roundtrip ───


def test_access_token_roundtrip() -> None:
    user_id = str(uuid4())
    token = create_access_token(user_id, role="admin")
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert payload["role"] == "admin"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload  # token rotation için unique id


def test_refresh_token_roundtrip() -> None:
    user_id = str(uuid4())
    token = create_refresh_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


def test_token_kid_header_present() -> None:
    """Token header'ında kid bulunmalı (rotation için)."""
    token = create_access_token(str(uuid4()))
    header = jose_jwt.get_unverified_header(token)
    assert header.get("kid") == settings.jwt_kid


# ─── JWT failure modes ───


def test_decode_garbage_token_raises() -> None:
    with pytest.raises(UnauthorizedError):
        decode_token("not.a.valid.jwt")


def test_decode_completely_invalid_string_raises() -> None:
    with pytest.raises(UnauthorizedError):
        decode_token("garbage")


def test_decode_expired_token_raises() -> None:
    """exp geçmiş — decode reddetmeli."""
    expired_token = _build_token(
        {"sub": "test", "type": "access"},
        timedelta(seconds=-10),
    )
    with pytest.raises(UnauthorizedError):
        decode_token(expired_token)


def test_decode_unknown_kid_raises() -> None:
    """Bilinmeyen kid header → UnauthorizedError (rotation senaryosu)."""
    payload = {"sub": "test", "type": "access"}
    token_with_bad_kid = jose_jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        headers={"kid": "non-existent-kid-v999"},
    )
    with pytest.raises(UnauthorizedError):
        decode_token(token_with_bad_kid)


def test_decode_wrong_signature_raises() -> None:
    """Farklı secret ile imzalı token → UnauthorizedError."""
    payload = {"sub": "test", "type": "access", "exp": 9999999999}
    token = jose_jwt.encode(
        payload,
        "completely_wrong_secret",
        algorithm=settings.jwt_algorithm,
        headers={"kid": settings.jwt_kid},
    )
    with pytest.raises(UnauthorizedError):
        decode_token(token)


# ─── kid rotation helpers ───


def test_resolve_secret_active_kid() -> None:
    """Aktif kid → mevcut secret döner."""
    secret = _resolve_secret(settings.jwt_kid)
    assert secret == settings.jwt_secret_key.get_secret_value()


def test_resolve_secret_no_kid_falls_back_to_active() -> None:
    """kid yoksa aktif secret kullanılır (eski tokenlar)."""
    secret = _resolve_secret(None)
    assert secret == settings.jwt_secret_key.get_secret_value()


def test_resolve_secret_unknown_kid_raises() -> None:
    with pytest.raises(UnauthorizedError) as exc_info:
        _resolve_secret("v0_does_not_exist")
    assert "kid" in exc_info.value.details
    assert exc_info.value.details["kid"] == "v0_does_not_exist"
