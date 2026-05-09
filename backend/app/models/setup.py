from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.symbol import Symbol
    from app.models.trade import Trade
    from app.models.user import User


class Setup(Base):
    __tablename__ = "setups"
    __table_args__ = (
        Index("idx_setups_active", "user_id", "status", text("created_at DESC")),
        Index("idx_setups_quality", "quality", postgresql_where=text("status = 'active'")),
        Index("idx_setups_type", "setup_type"),
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
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id")
    )

    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    quality: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    confluence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    macro_regime: Mapped[str | None] = mapped_column(String(30))
    risk_reward: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    setup_type: Mapped[str | None] = mapped_column(String(50))

    status: Mapped[str] = mapped_column(String(20), server_default="active", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="setups")
    symbol: Mapped["Symbol"] = relationship()
    analysis: Mapped["Analysis | None"] = relationship(back_populates="setups")
    trades: Mapped[list["Trade"]] = relationship(back_populates="setup")
