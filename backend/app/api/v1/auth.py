"""Auth endpoints: register, login, refresh, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.middleware import limiter
from app.core.security import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Yeni kullanıcı kaydı. Email çakışırsa 409."""
    return await auth_service.register_user(
        session=session,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(f"{settings.rate_limit_auth}/minute")
async def login(
    request: Request,  # slowapi key extraction (get_remote_address) için gerekli
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Email + şifre ile login. Rate limit: 5/dakika/IP."""
    user = await auth_service.authenticate(
        session=session,
        email=payload.email,
        password=payload.password,
    )
    access, refresh = auth_service.issue_token_pair(user.id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Refresh token ile yeni access+refresh pair al. Eski refresh blacklist'e atılır."""
    access, new_refresh, _user = await auth_service.rotate_refresh(
        session=session,
        refresh_token=payload.refresh_token,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Mevcut user bilgisi (Bearer token'dan)."""
    return current_user
