"""Async SQLAlchemy session.

Adım 2 geçici implementasyon — DATABASE_URL'i doğrudan env'den okur.
Adım 3'te `app.core.config.settings` tabanlı refactor edilecek.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://marketlens:marketlens_dev_password_change_me@postgres:5432/marketlens",
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — async DB session yield eder."""
    async with AsyncSessionLocal() as session:
        yield session
