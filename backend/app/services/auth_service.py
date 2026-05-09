"""Auth iş mantığı: register, authenticate, token issuance, refresh rotation."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.services import refresh_blacklist


async def register_user(
    session: AsyncSession,
    email: str,
    password: str,
    full_name: str | None = None,
    is_admin: bool = False,
) -> User:
    """Yeni user yarat. Email çakışırsa ConflictError."""
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ConflictError("Email zaten kayıtlı", details={"email": email})

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=True,
        is_admin=is_admin,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate(
    session: AsyncSession,
    email: str,
    password: str,
) -> User:
    """Email + şifre doğrula. Hata mesajı 'email yok' ve 'şifre yanlış' için aynı
    (enumeration safety)."""
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Email veya şifre yanlış")

    if not user.is_active:
        raise UnauthorizedError("Hesap deaktif")

    return user


def issue_token_pair(user_id: UUID | str) -> tuple[str, str]:
    """(access_token, refresh_token) üret."""
    return (
        create_access_token(user_id),
        create_refresh_token(user_id),
    )


async def rotate_refresh(
    session: AsyncSession,
    refresh_token: str,
) -> tuple[str, str, User]:
    """Refresh kullanılınca eski'yi blacklist'e at, yeni access+refresh ver.

    Hata durumları (UnauthorizedError):
    - Token signature/format/expiry geçersiz
    - type != "refresh"
    - jti blacklist'te (rotation theft detection)
    - User bulunamadı veya deaktif

    Returns: (new_access, new_refresh, user)
    """
    payload = decode_token(refresh_token)  # JWT signature + exp doğrular

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Geçerli refresh token değil")

    jti = payload.get("jti")
    if not jti:
        raise UnauthorizedError("Refresh token jti eksik")

    if await refresh_blacklist.is_revoked(jti):
        raise UnauthorizedError("Refresh token rotated, geçersiz")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Refresh token sub eksik")

    try:
        user_id = UUID(user_id_str)
    except ValueError as e:
        raise UnauthorizedError("Refresh token sub geçersiz UUID") from e

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedError("Kullanıcı bulunamadı veya aktif değil")

    # Eski refresh'i blacklist'e ekle (exp'a kadar)
    exp_timestamp = payload.get("exp")
    if exp_timestamp:
        exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        await refresh_blacklist.add(jti, exp_dt)

    # Yeni pair üret
    new_access, new_refresh = issue_token_pair(user.id)
    return new_access, new_refresh, user
