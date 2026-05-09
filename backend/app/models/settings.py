"""Kullanıcı ayarları + günlük risk takibi.

UserSettings 1:1 User; DailyRiskTracker 1:N User (her gün bir satır).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Risk yönetimi
    account_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), server_default="3000", nullable=False
    )
    risk_per_trade_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="2.0", nullable=False
    )
    max_leverage: Mapped[int] = mapped_column(Integer, server_default="10", nullable=False)
    daily_max_trades: Mapped[int] = mapped_column(Integer, server_default="5", nullable=False)
    daily_max_risk_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="4.0", nullable=False
    )
    auto_pause_after_losses: Mapped[int] = mapped_column(
        Integer, server_default="3", nullable=False
    )

    # Akıllı azaltma (smart_reduction)
    smart_reduction_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    risk_after_2_losses_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="1.5", nullable=False
    )
    risk_after_3_losses_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="1.0", nullable=False
    )

    # Volatility-adjusted
    volatility_adjustment_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )

    # Tarama
    scanner_enabled: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    scanner_interval_min: Mapped[int] = mapped_column(
        Integer, server_default="15", nullable=False
    )
    scanner_min_quality: Mapped[str] = mapped_column(String(1), server_default="B", nullable=False)

    # Volatility Alert eşikleri
    volatility_alert_5m_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="2.0", nullable=False
    )
    volatility_alert_1h_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="4.0", nullable=False
    )
    volatility_alert_4h_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="7.0", nullable=False
    )

    # Telegram
    telegram_alerts_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    alert_setup_found: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    alert_volatility: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    alert_critical_news: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    alert_stop_warn_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="1.0", nullable=False
    )
    alert_target_warn_pct: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), server_default="1.0", nullable=False
    )
    alert_funding_threshold: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), server_default="0.0500", nullable=False
    )
    alert_whale_threshold_usd: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), server_default="5000000", nullable=False
    )

    # No-trade zone
    no_trade_macro_events: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    no_trade_weekly_close: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    no_trade_high_volatility: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    no_trade_asian_session: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )

    # MA strategy
    auto_ma_selection: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )

    # Default UI
    default_timeframes: Mapped[list[str]] = mapped_column(
        ARRAY(String(10)), server_default="{4H,1D}", nullable=False
    )
    default_modules: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)), server_default="{trend,momentum,futures}", nullable=False
    )
    theme: Mapped[str] = mapped_column(String(20), server_default="dark", nullable=False)
    sidebar_collapsed: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )

    # AI Assistant (Faz 4) — şifrelenmiş key tutar
    anthropic_api_key: Mapped[str | None] = mapped_column(String(255))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="settings")


class DailyRiskTracker(Base):
    """Günlük risk durumu — kullanıcı + tarih unique."""

    __tablename__ = "daily_risk_tracker"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_risk_user_date"),)

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
    date: Mapped[date] = mapped_column(Date, nullable=False)

    trades_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    risk_used_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="0", nullable=False
    )
    consecutive_losses: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )

    # Smart reduction state
    current_risk_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    risk_reduction_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_paused: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    pause_reason: Mapped[str | None] = mapped_column(String(100))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="daily_risk_records")
