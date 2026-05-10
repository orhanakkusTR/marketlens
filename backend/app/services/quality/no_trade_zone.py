"""No-Trade Zone Detector — Adım 14.

9 zone tipi (bkz schemas/no_trade_zone.py). Detector saf fonksiyon mantığında:
  - Time-based (UTC referans, kullanıcı mesajlarında TR saati paralel)
  - Volatility-based (BTC 24h %|≥8| veya ATR z-score ≥ 2)
  - Range-based (BB squeeze + flat OBV)
  - DB-based (tilt: son 24h ardışık SL'ler)
  - Future-ready info zones (calendar, news, correlation, daily_risk)

Setup Quality entegrasyonunda:
  - ≥1 blocking → NO_TRADE hard override
  - ≥1 warning → grade -1 modifier
  - info → bilgi amaçlı, grade etkilemez

Severity desc sıralama: blocking → warning → info.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.trade import Trade
from app.schemas.indicators import VolatilityIndicators, VolumeIndicators
from app.schemas.no_trade_zone import (
    NoTradeZone,
    NoTradeZoneResult,
    NoTradeZoneSeverity,
    SeveritySummary,
)

logger = get_logger(__name__)

TR_TZ = ZoneInfo("Europe/Istanbul")

# Time windows (UTC)
LOW_LIQUIDITY_START_HOUR = 0
LOW_LIQUIDITY_END_HOUR = 8

# Weekend: Cuma 22:00 UTC → Pzt 02:00 UTC (52 saat)
WEEKEND_START_WEEKDAY = 4  # Friday (Mon=0)
WEEKEND_START_HOUR = 22
WEEKEND_END_WEEKDAY = 0  # Monday
WEEKEND_END_HOUR = 2

# Volatility thresholds
BTC_24H_VOLATILITY_PCT = 8.0
ATR_ZSCORE_HIGH = 2.0

# Tilt: son 24 saat
TILT_LOOKBACK_HOURS = 24
TILT_CONSECUTIVE_LOSSES = 3

SEVERITY_ORDER: dict[NoTradeZoneSeverity, int] = {
    "blocking": 0,
    "warning": 1,
    "info": 2,
}


def _format_utc_tr(now_utc: datetime) -> str:
    """'02:30 UTC / 05:30 TR' formatı."""
    tr = now_utc.astimezone(TR_TZ)
    return f"{now_utc:%H:%M} UTC / {tr:%H:%M} TR"


def _is_weekend_window(now_utc: datetime) -> bool:
    """Cuma 22:00 UTC ile Pazartesi 02:00 UTC arası."""
    weekday = now_utc.weekday()
    hour = now_utc.hour
    if weekday == WEEKEND_START_WEEKDAY:  # Cuma
        return hour >= WEEKEND_START_HOUR
    if weekday in (5, 6):  # Cumartesi, Pazar
        return True
    if weekday == WEEKEND_END_WEEKDAY:  # Pazartesi
        return hour < WEEKEND_END_HOUR
    return False


def _is_low_liquidity_session(now_utc: datetime) -> bool:
    """Asya seansı 00:00-08:00 UTC."""
    return LOW_LIQUIDITY_START_HOUR <= now_utc.hour < LOW_LIQUIDITY_END_HOUR


def _atr_zscore(atr_values: list[float]) -> float | None:
    """ATR'nin son 100 mum içindeki z-score'u (opsiyonel sinyal)."""
    if len(atr_values) < 20:
        return None
    series = pd.Series(atr_values)
    mean = float(series.mean())
    std = float(series.std(ddof=0))
    if std <= 0:
        return None
    return (atr_values[-1] - mean) / std


async def _consecutive_recent_losses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    now_utc: datetime,
) -> int:
    """Son 24h içindeki kapalı trade'lerden sondan başlayıp ardışık SL sayısı."""
    cutoff = now_utc - timedelta(hours=TILT_LOOKBACK_HOURS)
    stmt = (
        select(Trade.pnl_usd, Trade.exit_time)
        .where(
            Trade.status == "closed",
            Trade.exit_time.is_not(None),
            Trade.exit_time >= cutoff,
        )
        .order_by(Trade.exit_time.desc())
        .limit(20)
    )
    if user_id is not None:
        stmt = stmt.where(Trade.user_id == user_id)

    try:
        rows = (await session.execute(stmt)).all()
    except Exception as e:
        # DB hata → güvenli taraf: tilt yok kabul et
        logger.warning("tilt_query_failed", error=str(e))
        return 0

    consecutive = 0
    for row in rows:
        pnl = row.pnl_usd
        if pnl is None:
            break
        if float(pnl) < 0:
            consecutive += 1
        else:
            break
    return consecutive


class NoTradeZoneDetector:
    """Public facade — saf fonksiyon, time/state-based + DB query.

    `now_utc` parametresi test injection için (default: real time).
    """

    async def detect(
        self,
        *,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame | None = None,
        volatility: VolatilityIndicators | None = None,
        volume: VolumeIndicators | None = None,
        btc_24h_change_pct: float | None = None,
        atr_history: list[float] | None = None,
        session: AsyncSession | None = None,
        user_id: uuid.UUID | None = None,
        now_utc: datetime | None = None,
    ) -> NoTradeZoneResult:
        if now_utc is None:
            now_utc = datetime.now(UTC)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=UTC)

        zones: list[NoTradeZone] = []
        time_label = _format_utc_tr(now_utc)

        # 1. Weekend (blocking)
        if _is_weekend_window(now_utc):
            zones.append(
                NoTradeZone(
                    type="weekend",
                    severity="blocking",
                    message=(
                        f"Hafta sonu kapanış zonu — {time_label}. "
                        "Cuma 22:00 UTC ile Pazartesi 02:00 UTC arası likidite düşük, "
                        "spread geniş."
                    ),
                    advice="Pazartesi 02:00 UTC sonrası tekrar değerlendir.",
                    metadata={
                        "now_utc_iso": now_utc.isoformat(),
                        "weekday": now_utc.weekday(),
                    },
                )
            )

        # 2. Low liquidity session (warning)
        if _is_low_liquidity_session(now_utc):
            zones.append(
                NoTradeZone(
                    type="low_liquidity_session",
                    severity="warning",
                    message=(
                        f"Asya seansı düşük likidite — {time_label}. "
                        "00:00-08:00 UTC arası fiyat hareketleri sığ, false breakout riski."
                    ),
                    advice="Londra/NY seansını bekle (08:00 UTC sonrası).",
                    metadata={"hour_utc": now_utc.hour},
                )
            )

        # 3. High volatility (warning)
        high_vol_triggered = False
        high_vol_meta: dict[str, str | int | float | bool | None] = {}
        if (
            btc_24h_change_pct is not None
            and abs(btc_24h_change_pct) >= BTC_24H_VOLATILITY_PCT
        ):
            high_vol_triggered = True
            high_vol_meta["btc_24h_change_pct"] = round(btc_24h_change_pct, 2)
        if atr_history is not None:
            z = _atr_zscore(atr_history)
            if z is not None and z >= ATR_ZSCORE_HIGH:
                high_vol_triggered = True
                high_vol_meta["atr_zscore"] = round(z, 2)
        if high_vol_triggered:
            parts: list[str] = []
            if "btc_24h_change_pct" in high_vol_meta:
                parts.append(f"BTC 24h %{high_vol_meta['btc_24h_change_pct']:+}")
            if "atr_zscore" in high_vol_meta:
                parts.append(f"ATR z-score {high_vol_meta['atr_zscore']}")
            detail = " — ".join(parts) if parts else "Yüksek volatilite"
            zones.append(
                NoTradeZone(
                    type="high_volatility",
                    severity="warning",
                    message=(
                        f"Yüksek volatilite tespit edildi ({detail}). "
                        "Stop tetikleme ve slippage riski yüksek."
                    ),
                    advice="Pozisyon boyutunu yarıya indir veya volatilite normalleşene kadar bekle.",
                    metadata=high_vol_meta,
                )
            )

        # 4. Range market (warning) — sembol özel
        if volatility is not None and volume is not None:
            squeeze = volatility.bollinger.squeeze
            obv_flat = volume.obv.slope == "flat"
            if squeeze and obv_flat:
                zones.append(
                    NoTradeZone(
                        type="range_market",
                        severity="warning",
                        message=(
                            f"{symbol} {timeframe} sıkışık range — Bollinger squeeze + OBV yatay. "
                            "Trend pozisyonu zayıf, false breakout riski."
                        ),
                        advice="Range stratejisi (S/R bounce) düşün veya kırılım teyidi bekle.",
                        metadata={
                            "bb_width_pct": round(volatility.bollinger.width_pct, 2),
                            "obv_slope": volume.obv.slope,
                        },
                    )
                )

        # 5. Tilt (blocking) — DB query
        if session is not None:
            consecutive = await _consecutive_recent_losses(
                session, user_id=user_id, now_utc=now_utc
            )
            if consecutive >= TILT_CONSECUTIVE_LOSSES:
                zones.append(
                    NoTradeZone(
                        type="tilt",
                        severity="blocking",
                        message=(
                            f"Son 24 saatte {consecutive} ardışık SL — tilt riski. "
                            "Karar yorgunluğu ve duygusal işlem yapma riski yüksek."
                        ),
                        advice="En az 4 saat ara ver, journal'ı incele, ardından tekrar bak.",
                        metadata={
                            "consecutive_losses": consecutive,
                            "lookback_hours": TILT_LOOKBACK_HOURS,
                        },
                    )
                )

        # 6-9. Future-ready info zones (MVP: gösterge)
        zones.append(
            NoTradeZone(
                type="daily_risk_cap",
                severity="info",
                message="Günlük risk takibi: Adım 15 (risk_tracker) sonrası aktif.",
                advice=None,
                metadata={"future_step": 15},
            )
        )
        zones.append(
            NoTradeZone(
                type="major_event_proximity",
                severity="info",
                message="Ekonomik takvim entegrasyonu (CPI/FOMC/NFP ±4h): future.",
                advice=None,
                metadata={},
            )
        )
        zones.append(
            NoTradeZone(
                type="news_recent",
                severity="info",
                message="Haber feed entegrasyonu (CryptoPanic): future.",
                advice=None,
                metadata={},
            )
        )
        zones.append(
            NoTradeZone(
                type="correlation_risk",
                severity="info",
                message=(
                    "Korelasyon riski: açık pozisyonlarla overlap kontrolü — "
                    "açık pozisyon takibi (Adım 15+) sonrası aktif."
                ),
                advice=None,
                metadata={},
            )
        )

        # Severity desc sıralama (blocking → warning → info)
        zones.sort(key=lambda z: SEVERITY_ORDER[z.severity])

        # Summary
        summary = SeveritySummary(
            blocking=sum(1 for z in zones if z.severity == "blocking"),
            warning=sum(1 for z in zones if z.severity == "warning"),
            info=sum(1 for z in zones if z.severity == "info"),
        )
        is_blocking = summary.blocking > 0
        has_warning = summary.blocking + summary.warning > 0

        return NoTradeZoneResult(
            symbol=symbol,
            timeframe=timeframe,
            is_blocking=is_blocking,
            has_warning=has_warning,
            severity_summary=summary,
            zones=zones,
            computed_at=datetime.now(UTC),
            now_utc=now_utc,
        )


no_trade_zone_detector = NoTradeZoneDetector()
