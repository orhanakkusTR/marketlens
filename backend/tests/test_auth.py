"""Auth flow integration testleri (gerçek DB'ye yazıyor).

Her test unique email kullanır. Session sonunda `test-*@example.com` user'lar silinir.
slowapi rate limiter her test öncesi reset edilir (autouse fixture).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.middleware import limiter
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services import refresh_blacklist


# ─── Fixtures ───


@pytest.fixture(autouse=True)
async def _reset_auth_state() -> AsyncIterator[None]:
    """Her test öncesi blacklist + rate limiter temizlenir (test isolation)."""
    await refresh_blacklist.clear()
    limiter.reset()
    yield
    await refresh_blacklist.clear()
    limiter.reset()


@pytest.fixture(scope="session", autouse=True)
async def _cleanup_test_users_session() -> AsyncIterator[None]:
    """Session sonunda test-*@example.com user'larını siler (gerçek user'a dokunmaz)."""
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(User).where(User.email.like("test-%@example.com"))
        )
        await session.commit()


@pytest.fixture
def credentials() -> dict[str, str]:
    """Her test için unique email + güvenli şifre."""
    return {
        "email": f"test-{uuid4()}@example.com",
        "password": "secure_test_password_123",
        "full_name": "Test User",
    }


@pytest.fixture
async def registered_user(client: AsyncClient, credentials: dict) -> dict:
    """Kullanıcı kayıt et, credentials'ı geri döner (login için kullanılır)."""
    response = await client.post("/api/v1/auth/register", json=credentials)
    assert response.status_code == 201, response.text
    return credentials


# ─── Register ───


async def test_register_success(client: AsyncClient, credentials: dict) -> None:
    response = await client.post("/api/v1/auth/register", json=credentials)
    assert response.status_code == 201

    body = response.json()
    assert body["email"] == credentials["email"]
    assert body["full_name"] == credentials["full_name"]
    assert body["is_active"] is True
    assert body["is_admin"] is False
    assert "id" in body
    assert "created_at" in body
    # Sızıntı kontrolü
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email_409(
    client: AsyncClient, registered_user: dict
) -> None:
    response = await client.post("/api/v1/auth/register", json=registered_user)
    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


async def test_register_short_password_422(
    client: AsyncClient, credentials: dict
) -> None:
    payload = {**credentials, "password": "short"}  # 5 karakter, <8 minimum
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


async def test_register_invalid_email_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "secure_password_123"},
    )
    assert response.status_code == 422


# ─── Login ───


async def test_login_success(client: AsyncClient, registered_user: dict) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60  # 30 dk = 1800 sn


async def test_login_wrong_password_401(
    client: AsyncClient, registered_user: dict
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": "wrong_password_xyz_def",
        },
    )
    assert response.status_code == 401


async def test_login_unknown_email_401(
    client: AsyncClient, credentials: dict
) -> None:
    """Olmayan email — 'şifre yanlış' ile aynı 401 (enumeration safety)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": credentials["email"],  # Hiç kayıt edilmedi
            "password": credentials["password"],
        },
    )
    assert response.status_code == 401


async def test_login_rate_limit_429(
    client: AsyncClient, credentials: dict
) -> None:
    """5/dakika limit — 6. deneme 429 dönmeli."""
    # 5 başarısız deneme (yanlış şifre veya olmayan email)
    for _ in range(5):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": credentials["email"], "password": "any_password"},
        )
        assert r.status_code == 401  # her biri 401 (kullanıcı yok)

    # 6. deneme → rate limit
    r6 = await client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": "any_password"},
    )
    assert r6.status_code == 429
    assert r6.json()["error"] == "rate_limit_exceeded"


# ─── /me ───


async def test_me_with_valid_token(
    client: AsyncClient, registered_user: dict
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["email"] == registered_user["email"]
    assert body["full_name"] == registered_user["full_name"]
    assert body["is_admin"] is False
    assert "password_hash" not in body


async def test_me_without_token_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_invalid_token_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401


async def test_me_with_refresh_token_fails(
    client: AsyncClient, registered_user: dict
) -> None:
    """Refresh token ile /me çağrılırsa 401 (type kontrolü)."""
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401


# ─── Refresh ───


async def test_refresh_returns_new_pair(
    client: AsyncClient, registered_user: dict
) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    old_refresh = login.json()["refresh_token"]
    old_access = login.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert response.status_code == 200

    body = response.json()
    # Yeni pair eski'lerden farklı olmalı
    assert body["refresh_token"] != old_refresh
    assert body["access_token"] != old_access


async def test_refresh_rotation_blacklists_old(
    client: AsyncClient, registered_user: dict
) -> None:
    """Aynı refresh ikinci kez kullanılırsa 401 (theft detection)."""
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    refresh_token = login.json()["refresh_token"]

    # İlk refresh — başarı
    first = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert first.status_code == 200

    # Aynı eski refresh ile tekrar — blacklist'te
    second = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert second.status_code == 401


async def test_refresh_with_access_token_fails(
    client: AsyncClient, registered_user: dict
) -> None:
    """Access token /refresh'e verilince 401 (type kontrolü)."""
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    access_token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


async def test_refresh_with_garbage_token_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "garbage.token.string"},
    )
    assert response.status_code == 401
