"""Ekonomik takvim olayları (Faz 2'de forexfactory scrape ile dolar).

Faz 1'de manuel JSON dosyasından beslenir (no-trade zone tetiklemesi için).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EconomicEvent(Base):
    __tablename__ = "economic_events"
    __table_args__ = (
        UniqueConstraint("event_time", "name", "currency", name="uq_economic_event_time_name_ccy"),
        # NOT: Schema doc'unda `idx_events_upcoming ... WHERE event_time > NOW()` vardı.
        # Postgres partial index'leri IMMUTABLE predicate gerektirir, NOW() STABLE.
        # Bu yüzden WHERE clause'unu kaldırıp düz index kullanıyoruz.
        Index("idx_events_upcoming", "event_time"),
        Index(
            "idx_events_high_impact",
            "event_time",
            postgresql_where=text("impact = 'high'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str | None] = mapped_column(String(10))
    impact: Mapped[str | None] = mapped_column(String(20))
    forecast: Mapped[str | None] = mapped_column(String(50))
    previous: Mapped[str | None] = mapped_column(String(50))
    actual: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(50), server_default="forexfactory", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
