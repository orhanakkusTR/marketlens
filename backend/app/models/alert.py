"""Sistem alarmları (otomatik üretilir).

Manuel kullanıcı alarmları için ayrı `user_alerts` tablosu Adım 21B'de eklenecek.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    from app.models.setup import Setup
    from app.models.symbol import Symbol
    from app.models.trade import Trade
    from app.models.user import User


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alerts_user_undelivered", "user_id", "delivered", text("created_at DESC")),
        Index("idx_alerts_priority", "priority", text("created_at DESC")),
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
    symbol_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("symbols.id"))

    # alert_type değerleri: setup_found, price_target, stop_warning, target_warning,
    # funding_extreme, no_trade_zone_start, volatility_alert, critical_news,
    # whale_alert, sector_rotation
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    related_setup_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("setups.id")
    )
    related_trade_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("trades.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="alerts")
    symbol: Mapped["Symbol | None"] = relationship()
    related_setup: Mapped["Setup | None"] = relationship()
    related_trade: Mapped["Trade | None"] = relationship()
