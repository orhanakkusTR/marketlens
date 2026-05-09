"""DataService facade routing testi."""
from __future__ import annotations

from pytest_mock import MockerFixture

from app.services.data_service import DataService


async def test_data_service_routes_klines_to_binance(mocker: MockerFixture) -> None:
    svc = DataService()
    mock_klines = [{"open_time": 1, "close": 67000.0}]
    mocker.patch.object(svc.binance_spot, "get_klines", return_value=mock_klines)

    result = await svc.get_klines("BTCUSDT", "4H")
    assert result == mock_klines
    svc.binance_spot.get_klines.assert_awaited_once_with("BTCUSDT", "4H", 500)

    await svc.close()


async def test_data_service_routes_total_to_coingecko(mocker: MockerFixture) -> None:
    svc = DataService()
    mocker.patch.object(svc.coingecko, "get_total", return_value=2.5e12)

    result = await svc.get_total()
    assert result == 2.5e12

    await svc.close()


async def test_data_service_routes_dxy_to_yfinance(mocker: MockerFixture) -> None:
    svc = DataService()
    mocker.patch.object(svc.yfinance, "get_current_price", return_value=103.5)

    result = await svc.get_dxy()
    assert result == 103.5
    svc.yfinance.get_current_price.assert_awaited_once_with("DXY")

    await svc.close()


async def test_data_service_routes_funding_to_binance_futures(
    mocker: MockerFixture,
) -> None:
    svc = DataService()
    mock_funding = {"symbol": "BTCUSDT", "funding_rate": 0.0001}
    mocker.patch.object(
        svc.binance_futures, "get_funding_rate", return_value=mock_funding
    )

    result = await svc.get_funding("BTCUSDT")
    assert result == mock_funding

    await svc.close()
