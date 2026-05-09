"""Analiz çekirdek tabloları: analyses, confluence_scores, scenarios.

3 tablo aynı dosyada — sıkı bağlantılılar (Analysis 1:N ConfluenceScore, Analysis 1:N Scenario).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
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
    from app.models.setup import Setup
    from app.models.symbol import Symbol
    from app.models.trade import Trade
    from app.models.user import User


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("idx_analyses_user_symbol", "user_id", "symbol_id", text("created_at DESC")),
        Index(
            "idx_analyses_quality",
            "setup_quality",
            postgresql_where=text("setup_quality IN ('A', 'B')"),
        ),
        Index("idx_analyses_regime", "macro_regime", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    symbol_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("symbols.id"))
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    # Confluence
    overall_bias: Mapped[str | None] = mapped_column(String(20))
    alignment_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    alignment_label: Mapped[str | None] = mapped_column(String(20))

    # Setup quality
    setup_quality: Mapped[str | None] = mapped_column(CHAR(1))
    setup_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Confidence (MVP — kanıt seviyesi göstergesi)
    confidence_level: Mapped[str | None] = mapped_column(String(20))
    confidence_trade_count: Mapped[int | None] = mapped_column(Integer)
    actual_win_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Counter-trend (MVP — aldatıcı setup uyarıları)
    counter_trend_warnings_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    counter_trend_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Trade Quality Filter (MVP)
    trade_quality_score: Mapped[int | None] = mapped_column(Integer)
    trade_quality_verdict: Mapped[str | None] = mapped_column(String(20))
    trade_quality_factors: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Macro context
    macro_regime: Mapped[str | None] = mapped_column(String(30))
    macro_modifier: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # No-trade zone
    no_trade_active: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    no_trade_reason: Mapped[str | None] = mapped_column(String(255))

    # Time of day
    market_session: Mapped[str | None] = mapped_column(String(20))

    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User | None"] = relationship(back_populates="analyses")
    symbol: Mapped["Symbol | None"] = relationship()
    confluence_scores: Mapped[list["ConfluenceScore"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    scenarios: Mapped[list["Scenario"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    setups: Mapped[list["Setup"]] = relationship(back_populates="analysis")
    trades: Mapped[list["Trade"]] = relationship(back_populates="analysis")


class ConfluenceScore(Base):
    """Analysis 1:N — her timeframe için ayrı satır (lokal + macro + final)."""

    __tablename__ = "confluence_scores"
    __table_args__ = (Index("idx_confluence_analysis", "analysis_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)

    # Local layer
    local_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    trend_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    momentum_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    volume_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    volatility_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    futures_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Macro layer
    macro_modifier: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Final
    final_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    indicators: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analysis: Mapped["Analysis"] = relationship(back_populates="confluence_scores")


class Scenario(Base):
    """Analysis 1:N — tipik 2 senaryo: long ve short."""

    __tablename__ = "scenarios"
    __table_args__ = (Index("idx_scenarios_analysis", "analysis_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    probability: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    entry_low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    entry_high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    target_1: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    target_1_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="40", nullable=False
    )
    target_1_rationale: Mapped[str | None] = mapped_column(String(255))
    target_2: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    target_2_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="35", nullable=False
    )
    target_2_rationale: Mapped[str | None] = mapped_column(String(255))
    target_3: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    target_3_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), server_default="25", nullable=False
    )
    target_3_rationale: Mapped[str | None] = mapped_column(String(255))

    stop_loss: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    invalidation_note: Mapped[str | None] = mapped_column(String(255))

    risk_reward: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    atr_distance: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))

    support_levels: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    resistance_levels: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    summary_text: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analysis: Mapped["Analysis"] = relationship(back_populates="scenarios")
