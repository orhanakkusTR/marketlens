from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.watchlist import WatchlistSymbol


class AssetType(StrEnum):
    """asset_type alanı için izin verilen değerler."""

    CRYPTO = "crypto"
    COMMODITY = "commodity"


class Sector(StrEnum):
    """Sektör etiketleri (CLAUDE.md mapping'i ile birebir).

    Cross-asset rotation tracker bu etiketler üzerinde çalışır.
    """

    L1 = "L1"
    L2 = "L2"
    DEFI = "DeFi"
    MEME = "Meme"
    OTHER = "Other"
    COMMODITY = "Commodity"


class Symbol(Base):
    __tablename__ = "symbols"
    __table_args__ = (
        Index("idx_symbols_active", "is_active", "sort_order"),
        Index("idx_symbols_sector", "sector"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(20))
    quote_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    has_futures: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    # SQLAlchemy `Base.metadata` çakışmasını önlemek için Python attribute = `extra_metadata`,
    # PostgreSQL kolon adı `metadata` (database-schema.md spec'i).
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    watchlist_entries: Mapped[list["WatchlistSymbol"]] = relationship(
        back_populates="symbol", cascade="all, delete-orphan"
    )
