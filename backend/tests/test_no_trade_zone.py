"""No-Trade Zone Detector unit testleri.

Time-based zone'lar `now_utc` injection ile, range/tilt'ler synthetic data ile.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.indicators import (
    ATRResult,
    BollingerResult,
    OBVResult,
    VolatilityIndicators,
    VolumeIndicators,
    VolumeProfileResult,
)
from app.services.quality.no_trade_zone import (
    BTC_24H_VOLATILITY_PCT,
    TILT_CONSECUTIVE_LOSSES,
    no_trade_zone_detector,
)


def _vol(squeeze: bool = False, atr_pct: float = 1.5) -> VolatilityIndicators:
    return VolatilityIndicators(
        atr=ATRResult(value_usdt=1.5, value_pct=atr_pct, period=14),
        bollinger=BollingerResult(
            upper=105, middle=100, lower=95, width_pct=10.0, squeeze=squeeze
        ),
    )


def _volume(slope: str = "rising") -> VolumeIndicators:
    return VolumeIndicators(
        obv=OBVResult(current=1000.0, slope=slope),  # type: ignore[arg-type]
        vwap=None,
        volume_profile=VolumeProfileResult(
            poc=100, vah=102, val=98, total_volume=10000, bin_count=20, window_bars=30
        ),
    )


# ─── Time-based ───


async def test_weekend_friday_22_utc_blocking() -> None:
    """Cuma 22:00 UTC → weekend zone (blocking)."""
    # 2026-05-08 = Friday
    now = datetime(2026, 5, 8, 22, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    types = [z.type for z in result.zones if z.severity == "blocking"]
    assert "weekend" in types
    assert result.is_blocking is True


async def test_weekend_saturday_blocking() -> None:
    now = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)  # Cumartesi öğle
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    assert any(z.type == "weekend" and z.severity == "blocking" for z in result.zones)


async def test_weekend_monday_01_utc_still_blocking() -> None:
    now = datetime(2026, 5, 11, 1, 0, tzinfo=UTC)  # Pzt 01:00 UTC
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    assert any(z.type == "weekend" for z in result.zones)


async def test_weekend_monday_02_utc_clear() -> None:
    """Pzt 02:00 UTC tam — weekend kapanır."""
    now = datetime(2026, 5, 11, 2, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "weekend" not in types


async def test_weekend_friday_21_utc_not_yet() -> None:
    """Cuma 21:00 UTC — weekend henüz başlamadı."""
    now = datetime(2026, 5, 8, 21, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "weekend" not in types


async def test_low_liquidity_session_warning() -> None:
    """Salı 03:00 UTC = Asya seansı."""
    now = datetime(2026, 5, 12, 3, 0, tzinfo=UTC)  # Salı
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "low_liquidity_session" in types
    sess = next(z for z in result.zones if z.type == "low_liquidity_session")
    assert sess.severity == "warning"


async def test_low_liquidity_clear_after_8_utc() -> None:
    now = datetime(2026, 5, 12, 8, 0, tzinfo=UTC)  # Salı 08:00 UTC
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "low_liquidity_session" not in types


async def test_message_contains_utc_and_tr() -> None:
    """Mesaj formatı: 'XX:XX UTC / YY:YY TR'."""
    now = datetime(2026, 5, 12, 3, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    sess = next(z for z in result.zones if z.type == "low_liquidity_session")
    assert "UTC" in sess.message
    assert "TR" in sess.message


# ─── Volatility ───


async def test_high_volatility_btc_24h_8pct() -> None:
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)  # Çarşamba ortası
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT",
        timeframe="4H",
        btc_24h_change_pct=-9.5,
        now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "high_volatility" in types


async def test_high_volatility_below_threshold_clear() -> None:
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT",
        timeframe="4H",
        btc_24h_change_pct=3.5,
        now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "high_volatility" not in types


async def test_high_volatility_atr_zscore() -> None:
    """ATR z-score ≥ 2 → high_volatility tetikler."""
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    # 50 ATR değeri: ilk 49 sabit, son tane 4 sigma yukarı
    history = [1.0] * 49 + [10.0]
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT",
        timeframe="4H",
        atr_history=history,
        now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "high_volatility" in types


# ─── Range market ───


async def test_range_market_squeeze_plus_flat_obv() -> None:
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="ETHUSDT",
        timeframe="4H",
        volatility=_vol(squeeze=True),
        volume=_volume(slope="flat"),
        now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "range_market" in types


async def test_range_market_no_squeeze_clear() -> None:
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="ETHUSDT",
        timeframe="4H",
        volatility=_vol(squeeze=False),
        volume=_volume(slope="flat"),
        now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "range_market" not in types


async def test_range_market_no_flat_obv_clear() -> None:
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="ETHUSDT",
        timeframe="4H",
        volatility=_vol(squeeze=True),
        volume=_volume(slope="rising"),
        now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "range_market" not in types


# ─── Tilt (DB query) ───


async def test_tilt_3_consecutive_losses_blocking() -> None:
    """Mock session: 3 ardışık negatif pnl → tilt blocking."""
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    mock_session = MagicMock()
    rows = [
        MagicMock(pnl_usd=-50, exit_time=now),
        MagicMock(pnl_usd=-30, exit_time=now),
        MagicMock(pnl_usd=-20, exit_time=now),
        MagicMock(pnl_usd=100, exit_time=now),  # öncesinde win
    ]
    mock_session.execute = AsyncMock(return_value=MagicMock(all=lambda: rows))

    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", session=mock_session, now_utc=now,
    )
    types = [z.type for z in result.zones if z.severity == "blocking"]
    assert "tilt" in types


async def test_tilt_2_losses_below_threshold_clear() -> None:
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    mock_session = MagicMock()
    rows = [
        MagicMock(pnl_usd=-50, exit_time=now),
        MagicMock(pnl_usd=-30, exit_time=now),
        MagicMock(pnl_usd=100, exit_time=now),  # öncesinde win
    ]
    mock_session.execute = AsyncMock(return_value=MagicMock(all=lambda: rows))

    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", session=mock_session, now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "tilt" not in types


async def test_tilt_empty_db_no_zone() -> None:
    """Boş DB → tilt zone yok (future-ready, error olmadan 0 dön)."""
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(all=lambda: []))

    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", session=mock_session, now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "tilt" not in types


async def test_tilt_db_error_silent() -> None:
    """DB query exception → tilt yok kabul, hata yutulur."""
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=Exception("connection lost"))

    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", session=mock_session, now_utc=now,
    )
    types = [z.type for z in result.zones]
    assert "tilt" not in types


# ─── Future-ready info zones ───


async def test_info_zones_always_present() -> None:
    """4 future-ready info zone her zaman dönmeli."""
    now = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    info_types = {z.type for z in result.zones if z.severity == "info"}
    assert info_types == {
        "daily_risk_cap",
        "major_event_proximity",
        "news_recent",
        "correlation_risk",
    }


# ─── Severity sorting ───


async def test_severity_desc_sorted() -> None:
    """Sıralama: blocking → warning → info."""
    now = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)  # Cumartesi (weekend blocking)
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT",
        timeframe="4H",
        btc_24h_change_pct=-10.0,  # high_volatility warning
        volatility=_vol(squeeze=True),
        volume=_volume(slope="flat"),  # range_market warning
        now_utc=now,
    )
    severities = [z.severity for z in result.zones]
    # Sondaki info'lar; başta blocking; ortada warning'ler
    assert severities[0] == "blocking"
    # info hep en sonda
    info_indices = [i for i, s in enumerate(severities) if s == "info"]
    if info_indices:
        assert min(info_indices) > severities.index("warning") if "warning" in severities else True
        # Tüm info'lar warning'lerden sonra
        last_warning = max(
            (i for i, s in enumerate(severities) if s == "warning"),
            default=-1,
        )
        assert min(info_indices) > last_warning


async def test_summary_counts_match() -> None:
    now = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)  # Cumartesi
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now,
    )
    summary = result.severity_summary
    assert summary.blocking == sum(1 for z in result.zones if z.severity == "blocking")
    assert summary.warning == sum(1 for z in result.zones if z.severity == "warning")
    assert summary.info == sum(1 for z in result.zones if z.severity == "info")


async def test_is_blocking_flag() -> None:
    now_blocking = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)  # Cumartesi
    result_b = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now_blocking,
    )
    assert result_b.is_blocking is True

    now_clean = datetime(2026, 5, 13, 14, 0, tzinfo=UTC)  # Çarşamba 14:00 UTC
    result_c = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=now_clean,
    )
    assert result_c.is_blocking is False


async def test_naive_datetime_treated_as_utc() -> None:
    """tzinfo'suz datetime UTC olarak yorumlanır."""
    naive = datetime(2026, 5, 9, 12, 0)
    result = await no_trade_zone_detector.detect(
        symbol="BTCUSDT", timeframe="4H", now_utc=naive,
    )
    # Cumartesi → weekend
    assert result.is_blocking is True


# ─── Constants sanity ───


def test_constants() -> None:
    assert BTC_24H_VOLATILITY_PCT == 8.0
    assert TILT_CONSECUTIVE_LOSSES == 3


# ─── Endpoint smoke ───


@pytest.mark.integration
async def test_endpoint_btc_4h(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/no-trade-zones/BTCUSDT/4H")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSDT"
    assert body["timeframe"] == "4H"
    # Future-ready info zone'lar her zaman olmalı (4 adet)
    info_count = body["severity_summary"]["info"]
    assert info_count >= 4
    # Severity desc sıralı
    severities = [z["severity"] for z in body["zones"]]
    blocking_idx = [i for i, s in enumerate(severities) if s == "blocking"]
    info_idx = [i for i, s in enumerate(severities) if s == "info"]
    if blocking_idx and info_idx:
        assert max(blocking_idx) < min(info_idx)


@pytest.mark.integration
async def test_endpoint_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/no-trade-zones/FOOBAR/4H")
    assert r.status_code == 404


@pytest.mark.integration
async def test_endpoint_invalid_tf(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/analysis/no-trade-zones/BTCUSDT/2H")
    assert r.status_code == 422
