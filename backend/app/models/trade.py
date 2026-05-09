from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    ARRAY,
    CHAR,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.setup import Setup
    from app.models.symbol import Symbol
    from app.models.user import User


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        Index("idx_trades_user_status", "user_id", "status", text("entry_time DESC")),
        Index(
            "idx_trades_closed",
            "user_id",
            text("exit_time DESC"),
            postgresql_where=text("status = 'closed'"),
        ),
        Index(
            "idx_trades_setup_type",
            "setup_type",
            postgresql_where=text("status = 'closed'"),
        ),
        Index(
            "idx_trades_session",
            "market_session",
            postgresql_where=text("status = 'closed'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[int] = mapped_column(Integer, ForeignKey("symbols.id"), nullable=False)
    setup_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("setups.id")
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id")
    )

    direction: Mapped[str] = mapped_column(String(10), nullable=False)

    # Giriş
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    position_size_usd: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_used: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)

    # Plan
    planned_stop: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    planned_target1: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    planned_target2: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    planned_target3: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))

    # Çıkış
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exit_reason: Mapped[str | None] = mapped_column(String(50))

    # Sonuç
    pnl_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pnl_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    r_multiple: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    funding_paid: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), server_default="0", nullable=False
    )
    fees_paid: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), server_default="0", nullable=False
    )

    # Meta
    setup_quality_at_entry: Mapped[str | None] = mapped_column(CHAR(1))
    macro_regime_at_entry: Mapped[str | None] = mapped_column(String(30))
    timeframe: Mapped[str | None] = mapped_column(String(10))
    market_session: Mapped[str | None] = mapped_column(String(20))
    setup_type: Mapped[str | None] = mapped_column(String(50))
    user_note: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(50)))

    # Position management
    trailing_stop_active: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    breakeven_set: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    partial_closes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    status: Mapped[str] = mapped_column(String(20), server_default="open", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="trades")
    symbol: Mapped["Symbol"] = relationship()
    setup: Mapped["Setup | None"] = relationship(back_populates="trades")
    analysis: Mapped["Analysis | None"] = relationship(back_populates="trades")
