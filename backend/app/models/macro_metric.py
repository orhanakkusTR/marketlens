from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MacroMetric(Base):
    """Makro metrikler zaman serisi.

    metric_code örnekleri: TOTAL, TOTAL2, TOTAL3, BTC.D, ETH.D,
    DXY, SP500, VIX, US10Y, ETH_BTC.
    """

    __tablename__ = "macro_metrics"
    __table_args__ = (
        UniqueConstraint("metric_code", "timestamp", name="uq_macro_metric_code_ts"),
        Index("idx_macro_metrics_lookup", "metric_code", text("timestamp DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric_code: Mapped[str] = mapped_column(String(30), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(30, 8), nullable=False)
