"""JWT (kid header'lı) + bcrypt password hashing + get_current_user dependency.

JWT imzalama anahtarı rotasyonu için kid (key ID) header'ı kullanılır:
- Aktif kid: settings.jwt_kid (default "v1")
- Eski kid'ler: settings.jwt_old_secrets (grace period için)

Rotasyon: JWT_KID=v2, JWT_SECRET_KEY=<new>, JWT_OLD_SECRETS='{"v1":"<old>"}'.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.db.session import get_session
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Password hashing ───


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT ───


def _resolve_secret(kid: str | None) -> str:
    """Token'ın kid header'ına göre verify secret'ı seç."""
    if kid is None or kid == settings.jwt_kid:
        return settings.jwt_secret_key.get_secret_value()
    if kid in settings.jwt_old_secrets:
        return settings.jwt_old_secrets[kid].get_secret_value()
    raise UnauthorizedError(
        "Bilinmeyen JWT key id",
        details={"kid": kid},
    )


def _build_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        **payload,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        headers={"kid": settings.jwt_kid},
    )


def create_access_token(subject: str | UUID, **extra_claims: Any) -> str:
    return _build_token(
        {"sub": str(subject), "type": "access", **extra_claims},
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(subject: str | UUID) -> str:
    return _build_token(
        {"sub": str(subject), "type": "refresh"},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """İmza + expiry doğrulama. Hata durumunda UnauthorizedError fırlatır."""
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise UnauthorizedError("Geçersiz token formatı") from e

    secret = _resolve_secret(header.get("kid"))

    try:
        return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise UnauthorizedError("Geçersiz veya süresi dolmuş token") from e


# ─── FastAPI dependency ───


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Authorization: Bearer <token> header'ından user yükler.

    Eksik/geçersiz token, expired token, deaktif kullanıcı → UnauthorizedError (401).
    """
    if credentials is None:
        raise UnauthorizedError("Bearer token eksik")

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise UnauthorizedError("Geçerli bir access token değil")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Token sub claim eksik")

    try:
        user_id = UUID(user_id_str)
    except ValueError as e:
        raise UnauthorizedError("Token sub geçersiz UUID") from e

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedError("Kullanıcı bulunamadı veya aktif değil")

    return user
