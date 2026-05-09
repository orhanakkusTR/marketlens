"""Data client unit testleri (mock'lu).

Cache cleanup fixture her test öncesi cache key'lerini temizler ki
mock'lanmış response'lar gerçekten kullanılsın.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from pytest_mock import MockerFixture

from app.core.redis_client import redis_client
from app.data.binance_depth import BinanceDepthClient
from app.data.binance_futures import BinanceFuturesClient
from app.data.binance_spot import BinanceSpotClient
from app.data.coingecko import CoinGeckoClient
from app.data.fear_greed import AlternativeMeClient


@pytest.fixture(autouse=True)
async def _clear_data_cache_keys() -> AsyncIterator[None]:
    """Test öncesi cache key'lerini sil ki mock response'lar yeni keylere yazılsın."""
    patterns = [
        "marketlens:binance:*",
        "marketlens:cg:*",
        "marketlens:fng:*",
    ]
    for pattern in patterns:
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
    yield


# ─── Binance Spot ───


async def test_binance_klines_parses_correctly(mocker: MockerFixture) -> None:
    client = BinanceSpotClient()

    raw_klines = [
        [
            1700000000000, "67000.00", "67500.00", "66800.00", "67200.00",
            "100.5", 1700014399999, "6750000.00", 200, "50.5", "3375000.00", "0",
        ],
    ]
    mock_response = httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw_klines)
    mocker.patch.object(client._http, "request", return_value=mock_response)

    klines = await client.get_klines("BTCUSDT", "4H", limit=1)
    assert len(klines) == 1
    k = klines[0]
    assert k["open_time"] == 1700000000000
    assert k["open"] == 67000.0
    assert k["high"] == 67500.0
    assert k["close"] == 67200.0
    assert k["volume"] == 100.5
    assert k["trades"] == 200

    await client.close()


async def test_binance_klines_invalid_timeframe_raises() -> None:
    client = BinanceSpotClient()
    with pytest.raises(ValueError, match="Bilinmeyen timeframe"):
        await client.get_klines("BTCUSDT", "INVALID")
    await client.close()


async def test_binance_ticker_price(mocker: MockerFixture) -> None:
    client = BinanceSpotClient()
    mock_response = httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json={"symbol": "BTCUSDT", "price": "67432.50"})
    mocker.patch.object(client._http, "request", return_value=mock_response)

    price = await client.get_ticker_price("BTCUSDT")
    assert price == 67432.50

    await client.close()


# ─── Binance Futures ───


async def test_binance_funding_parses(mocker: MockerFixture) -> None:
    client = BinanceFuturesClient()
    raw = {
        "symbol": "BTCUSDT",
        "markPrice": "67000.50",
        "indexPrice": "67005.00",
        "lastFundingRate": "0.00012345",
        "nextFundingTime": 1700100000000,
        "interestRate": "0.0001",
        "time": 1700000000000,
    }
    mocker.patch.object(client._http, "request", return_value=httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw))

    funding = await client.get_funding_rate("BTCUSDT")
    assert funding["symbol"] == "BTCUSDT"
    assert funding["mark_price"] == 67000.50
    assert funding["funding_rate"] == 0.00012345
    assert funding["next_funding_time"] == 1700100000000

    await client.close()


async def test_binance_open_interest_parses(mocker: MockerFixture) -> None:
    client = BinanceFuturesClient()
    raw = {"symbol": "BTCUSDT", "openInterest": "75000.123", "time": 1700000000000}
    mocker.patch.object(client._http, "request", return_value=httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw))

    oi = await client.get_open_interest("BTCUSDT")
    assert oi["open_interest"] == 75000.123

    await client.close()


async def test_binance_long_short_ratio_parses(mocker: MockerFixture) -> None:
    client = BinanceFuturesClient()
    raw = [
        {
            "symbol": "BTCUSDT",
            "longShortRatio": "1.5432",
            "longAccount": "0.6068",
            "shortAccount": "0.3932",
            "timestamp": 1700000000000,
        }
    ]
    mocker.patch.object(client._http, "request", return_value=httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw))

    lsr = await client.get_long_short_ratio("BTCUSDT")
    assert len(lsr) == 1
    assert lsr[0]["long_short_ratio"] == 1.5432
    assert lsr[0]["long_account"] == 0.6068

    await client.close()


# ─── Binance Depth ───


async def test_binance_orderbook_parses(mocker: MockerFixture) -> None:
    client = BinanceDepthClient()
    raw = {
        "lastUpdateId": 12345,
        "bids": [["67000.00", "1.5"], ["66999.50", "2.0"]],
        "asks": [["67001.00", "0.8"], ["67001.50", "1.2"]],
    }
    mocker.patch.object(client._http, "request", return_value=httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw))

    book = await client.get_orderbook("BTCUSDT", limit=10)
    assert book["last_update_id"] == 12345
    assert book["bids"][0] == [67000.0, 1.5]
    assert book["asks"][0] == [67001.0, 0.8]

    await client.close()


# ─── CoinGecko ───


async def test_coingecko_global_extracts_data(mocker: MockerFixture) -> None:
    client = CoinGeckoClient()
    raw = {
        "data": {
            "total_market_cap": {"usd": 2.5e12},
            "market_cap_percentage": {"btc": 50.0, "eth": 17.5},
        }
    }
    mocker.patch.object(client._http, "request", return_value=httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw))

    data = await client.get_global()
    assert data["total_market_cap"]["usd"] == 2.5e12
    assert data["market_cap_percentage"]["btc"] == 50.0

    await client.close()


async def test_coingecko_total2_total3_calculation(mocker: MockerFixture) -> None:
    client = CoinGeckoClient()
    raw = {
        "data": {
            "total_market_cap": {"usd": 2_000_000_000_000.0},
            "market_cap_percentage": {"btc": 50.0, "eth": 20.0},
        }
    }
    mocker.patch.object(client._http, "request", return_value=httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw))

    total = await client.get_total()
    total2 = await client.get_total2()
    total3 = await client.get_total3()

    assert total == pytest.approx(2_000_000_000_000.0)
    # TOTAL2 = 2T * (1 - 0.5) = 1T
    assert total2 == pytest.approx(1_000_000_000_000.0)
    # TOTAL3 = 2T * (1 - 0.7) = 600B
    assert total3 == pytest.approx(600_000_000_000.0)

    await client.close()


async def test_coingecko_dominances(mocker: MockerFixture) -> None:
    client = CoinGeckoClient()
    raw = {
        "data": {
            "total_market_cap": {"usd": 2e12},
            "market_cap_percentage": {"btc": 54.2, "eth": 16.5},
        }
    }
    mocker.patch.object(client._http, "request", return_value=httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw))

    btc_d = await client.get_btc_dominance()
    eth_d = await client.get_eth_dominance()
    assert btc_d == 54.2
    assert eth_d == 16.5

    await client.close()


# ─── Fear & Greed ───


async def test_fear_greed_parses_response(mocker: MockerFixture) -> None:
    client = AlternativeMeClient()
    raw = {
        "data": [
            {"value": "65", "value_classification": "Greed", "timestamp": "1700000000"}
        ],
        "metadata": {"error": None},
    }
    mocker.patch.object(client._http, "request", return_value=httpx.Response(request=httpx.Request("GET", "http://test"), status_code=200, json=raw))

    fg = await client.get_fear_greed()
    assert fg["value"] == 65
    assert fg["classification"] == "Greed"
    assert fg["timestamp"] == "1700000000"

    await client.close()
