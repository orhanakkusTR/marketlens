from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceCache(Base):
    """OHLCV mum verisi DB cache'i. Redis cache'i tamamlayıcı, uzun vadeli sorgular için."""

    __tablename__ = "price_cache"
    __table_args__ = (
        UniqueConstraint(
            "symbol_id", "timeframe", "open_time", name="uq_price_cache_symbol_tf_time"
        ),
        Index("idx_price_cache_lookup", "symbol_id", "timeframe", text("open_time DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol_id: Mapped[int] = mapped_column(Integer, ForeignKey("symbols.id"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 8))
    trade_count: Mapped[int | None] = mapped_column(Integer)
