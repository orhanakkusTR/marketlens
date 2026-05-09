from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Correlation(Base):
    """30 günlük log returns Pearson korelasyonu (cron her saat günceller)."""

    __tablename__ = "correlations"
    __table_args__ = (
        Index(
            "idx_correlations_lookup",
            "symbol_a_id",
            "symbol_b_code",
            text("computed_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    symbol_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("symbols.id"), nullable=False)
    # B tarafı string (BTC, ETH, TOTAL3, DXY, SP500 vs. — sadece kod, FK yok)
    symbol_b_code: Mapped[str] = mapped_column(String(20), nullable=False)
    period_days: Mapped[int] = mapped_column(Integer, server_default="30", nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), server_default="4H", nullable=False)
    correlation: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
