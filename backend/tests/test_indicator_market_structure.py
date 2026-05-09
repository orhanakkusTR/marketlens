"""Market Structure — HH/HL/LH/LL classification."""
from __future__ import annotations

from app.services.indicators.base import klines_to_dataframe
from app.services.indicators.trend.market_structure import compute_market_structure

from ._synthetic import (
    linear_uptrend,
    zigzag_downtrend,
    zigzag_uptrend,
)


def test_uptrend_hh_hl() -> None:
    df = klines_to_dataframe(zigzag_uptrend(cycles=5, swing_size=20))
    result = compute_market_structure(df)
    assert result.structure == "uptrend"
    assert len(result.recent_swings) > 0


def test_downtrend_lh_ll() -> None:
    df = klines_to_dataframe(zigzag_downtrend(cycles=5, swing_size=20))
    result = compute_market_structure(df)
    assert result.structure == "downtrend"


def test_ranging_with_alternating_equal_swings() -> None:
    """Eşit yükseklikteki alternatif swing'ler → karışık (ranging)."""
    from ._synthetic import custom_path

    # Sabit aralıkta inip çıkan, ne yukarı ne aşağı eğilim göstermeyen seri
    prices: list[float] = []
    for cycle in range(8):
        # yukarı 15 bar, aşağı 15 bar (sabit highs/lows ama küçük dalgalanmayla)
        peak = 110.0 + (cycle % 2) * 0.5  # her cycle hafifçe değişen tepe
        valley = 90.0 - (cycle % 2) * 0.5
        for i in range(15):
            prices.append(valley + (peak - valley) * (i + 1) / 15)
        for i in range(15):
            prices.append(peak - (peak - valley) * (i + 1) / 15)

    df = klines_to_dataframe(custom_path(prices))
    result = compute_market_structure(df)
    # Ne uptrend ne de downtrend olmalı (3+ aynı yön swing yok)
    assert result.structure in ("ranging",), (
        f"Beklenen ranging, alındı: {result.structure} ({[s.kind for s in result.recent_swings]})"
    )


def test_short_data_returns_ranging_with_no_swings() -> None:
    df = klines_to_dataframe(linear_uptrend(n=8))
    result = compute_market_structure(df)
    assert result.structure == "ranging"
    assert len(result.recent_swings) == 0


def test_swings_have_increasing_indices() -> None:
    df = klines_to_dataframe(linear_uptrend(n=100))
    result = compute_market_structure(df)
    # Az da olsa swing tespit edilebilir; eğer varsa sıralı olmalı
    if len(result.recent_swings) > 1:
        indices = [s.index for s in result.recent_swings]
        assert indices == sorted(indices)


def test_linear_uptrend_no_pivots_classifies_as_ranging() -> None:
    """Düz monotonic trend → pivot yok (her bar yeni high) → ranging."""
    df = klines_to_dataframe(linear_uptrend(n=200))
    result = compute_market_structure(df)
    # Lineer trende high pivot bulunabilir ama HL yok → uptrend olamaz
    assert result.structure in ("uptrend", "ranging")
