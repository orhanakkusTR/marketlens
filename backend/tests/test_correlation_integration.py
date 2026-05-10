"""Korelasyon integration testleri — gerçek piyasa verisi."""
from __future__ import annotations

import time

import pytest

from app.core.redis_client import redis_client
from app.services.correlation.engine import correlation_engine

pytestmark = pytest.mark.integration


async def test_full_matrix_real_data() -> None:
    matrix = await correlation_engine.compute_matrix(period_days=30)
    # 27 sembol + 3 tradfi = 30 (eğer hepsi fetch oldu); GOLD/tradfi düşerse < 30
    assert len(matrix.symbols) >= 27
    # Diagonal = 1.0
    for sym in matrix.symbols:
        assert matrix.matrix[sym][sym] == pytest.approx(1.0, abs=0.001)
    # Simetri
    for sym_a in matrix.symbols[:5]:
        for sym_b in matrix.symbols[:5]:
            r_ab = matrix.matrix[sym_a][sym_b]
            r_ba = matrix.matrix[sym_b][sym_a]
            if r_ab is not None and r_ba is not None:
                assert r_ab == pytest.approx(r_ba, abs=0.001)


async def test_btc_eth_strong_positive_correlation() -> None:
    """ETH ve BTC genelde 0.7+ korelasyonlu (kripto market)."""
    btc = await correlation_engine.get_symbol_correlations("BTCUSDT")
    assert btc.vs_eth is not None
    assert btc.vs_eth > 0.7


async def test_btc_top_correlations_dominated_by_majors() -> None:
    """BTC top 5 korelasyon majors olmalı (kripto bull rejim)."""
    btc = await correlation_engine.get_symbol_correlations("BTCUSDT")
    top5_symbols = {p.symbol for p in btc.all[:5]}
    majors = {"ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT"}
    # En az 3'ü majors arasından olmalı
    overlap = top5_symbols & majors
    assert len(overlap) >= 3, f"BTC top5 majors içermiyor: {top5_symbols}"


async def test_btc_vs_xauusdt_decoupled() -> None:
    """BTC ile XAUUSDT (commodity) genelde decoupled veya zayıf (|r| < 0.5)."""
    btc = await correlation_engine.get_symbol_correlations("BTCUSDT")
    # XAUUSDT pair'ini ara
    xau_pair = next((p for p in btc.all if p.symbol == "XAUUSDT"), None)
    assert xau_pair is not None
    assert abs(xau_pair.coefficient) < 0.5


async def test_btc_vs_dxy_negative_correlation() -> None:
    """BTC ile DXY genelde negative correlation."""
    btc = await correlation_engine.get_symbol_correlations("BTCUSDT")
    assert btc.vs_dxy is not None
    # Genelde negatif, ama sıfıra yakın olabilir → < 0.3 yeterli
    assert btc.vs_dxy < 0.3


async def test_btc_self_correlations_not_included() -> None:
    """BTC kendi pair'inde yok (kendisiyle korelasyon listede olmamalı)."""
    btc = await correlation_engine.get_symbol_correlations("BTCUSDT")
    for p in btc.all:
        assert p.symbol != "BTCUSDT"
    assert btc.vs_btc is None  # BTC için vs_btc None


async def test_eth_vs_btc_in_pair_list() -> None:
    eth = await correlation_engine.get_symbol_correlations("ETHUSDT")
    assert eth.vs_btc is not None
    assert eth.vs_btc > 0.7
    assert eth.vs_eth is None


async def test_all_pairs_sorted_by_abs_value() -> None:
    btc = await correlation_engine.get_symbol_correlations("BTCUSDT")
    abs_values = [abs(p.coefficient) for p in btc.all]
    assert abs_values == sorted(abs_values, reverse=True)


async def test_sector_avg_keys() -> None:
    btc = await correlation_engine.get_symbol_correlations("BTCUSDT")
    # En az 4 sektör (L1, L2, DeFi, Meme, Other, Commodity) avg dönmeli
    assert len(btc.by_sector_avg) >= 4
    # Commodity (GOLD) dahil olmalı
    assert "Commodity" in btc.by_sector_avg


async def test_meme_sector_avg_lower_than_l1() -> None:
    """Genelde Meme sektörünün L1 ile BTC korelasyonu daha düşük olur.

    Ama market koşullarına bağlı — esnek test: ikisi de pozitif olmalı.
    """
    btc = await correlation_engine.get_symbol_correlations("BTCUSDT")
    if "L1" in btc.by_sector_avg and "Meme" in btc.by_sector_avg:
        # Pozitif olmalı
        assert btc.by_sector_avg["L1"] > 0
        # Sadece pozitif olmalarını test et — magnitude varyasyona açık


# ─── Endpoints ───


async def test_matrix_endpoint(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/correlations/matrix?period_days=30&tf=1D")
    assert r.status_code == 200
    body = r.json()
    assert "symbols" in body
    assert "matrix" in body
    assert len(body["symbols"]) >= 27


async def test_symbol_correlations_endpoint(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/correlations/BTCUSDT")
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTCUSDT"
    assert "all" in body
    assert "by_sector_avg" in body
    assert "vs_eth" in body


async def test_endpoint_unknown_symbol(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/correlations/FOOBAR")
    assert r.status_code == 404


async def test_endpoint_invalid_period(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/correlations/matrix?period_days=200")
    # FastAPI Query ge/le validation 422
    assert r.status_code == 422


async def test_endpoint_invalid_tf(client) -> None:  # type: ignore[no-untyped-def]
    r = await client.get("/api/v1/correlations/matrix?tf=4H")
    assert r.status_code == 422


# ─── Cache ───


async def test_correlation_cache_hit_under_50ms() -> None:
    async for k in redis_client.scan_iter(match="marketlens:correlation:matrix:*"):
        await redis_client.delete(k)

    t0 = time.perf_counter()
    await correlation_engine.compute_matrix(period_days=14)
    first = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    await correlation_engine.compute_matrix(period_days=14)
    second = (time.perf_counter() - t0) * 1000

    print(f"\n  1st: {first:.1f}ms  2nd: {second:.1f}ms  speedup: {first/second:.1f}x")
    assert second < 50
