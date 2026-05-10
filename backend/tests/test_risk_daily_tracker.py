"""Daily Risk Tracker testleri — consecutive losses, smart reduction, pause."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.redis_client import redis_client
from app.services.risk.daily_tracker import (
    DAILY_MAX_RISK_PCT,
    DAILY_MAX_TRADES,
    DEFAULT_RISK_PCT,
    PAUSE_DEFAULT_HOURS,
    SMART_REDUCTION_2_LOSSES_PCT,
    SMART_REDUCTION_3_LOSSES_PCT,
    REDIS_PAUSE_GLOBAL_KEY,
    REDIS_PAUSE_KEY_PREFIX,
    daily_risk_tracker,
)


def _mock_session_with_pnls(pnls: list[float]) -> MagicMock:
    """trades.pnl_usd sorgu sonuçları için mock."""
    rows = [MagicMock() for _ in pnls]
    for r, p in zip(rows, pnls):
        # row[0] = pnl_usd
        r.__getitem__ = lambda self, idx, p=p: p
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(all=lambda: rows))
    return mock_session


# ─── Consecutive losses ───


async def test_consecutive_losses_zero_empty() -> None:
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(all=lambda: []))
    n = await daily_risk_tracker.get_consecutive_losses(mock_session, user_id=None)
    assert n == 0


async def test_consecutive_losses_3_then_win() -> None:
    """[-50, -30, -20, +100] → 3 ardışık (sondan başla)."""
    mock_session = _mock_session_with_pnls([-50, -30, -20, 100])
    n = await daily_risk_tracker.get_consecutive_losses(mock_session, user_id=None)
    assert n == 3


async def test_consecutive_losses_stops_at_first_win() -> None:
    mock_session = _mock_session_with_pnls([-50, 100, -30, -20])
    n = await daily_risk_tracker.get_consecutive_losses(mock_session, user_id=None)
    assert n == 1


async def test_consecutive_losses_db_error_returns_zero() -> None:
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=Exception("db down"))
    n = await daily_risk_tracker.get_consecutive_losses(mock_session, user_id=None)
    assert n == 0


# ─── Smart reduction ───


async def test_smart_reduction_default_2pct() -> None:
    mock_session = _mock_session_with_pnls([100, 50])  # win + win
    pct, active, losses = await daily_risk_tracker.get_current_risk_per_trade_pct(
        mock_session, user_id=None
    )
    assert pct == DEFAULT_RISK_PCT
    assert active is False
    assert losses == 0


async def test_smart_reduction_2_losses() -> None:
    mock_session = _mock_session_with_pnls([-50, -30, 100])
    pct, active, losses = await daily_risk_tracker.get_current_risk_per_trade_pct(
        mock_session, user_id=None
    )
    assert pct == SMART_REDUCTION_2_LOSSES_PCT
    assert active is True
    assert losses == 2


async def test_smart_reduction_3_losses() -> None:
    mock_session = _mock_session_with_pnls([-50, -30, -20, 100])
    pct, active, losses = await daily_risk_tracker.get_current_risk_per_trade_pct(
        mock_session, user_id=None
    )
    assert pct == SMART_REDUCTION_3_LOSSES_PCT
    assert active is True
    assert losses == 3


async def test_smart_reduction_5_losses_still_1pct() -> None:
    """3+ tüm seviyeler için %1."""
    mock_session = _mock_session_with_pnls([-50, -30, -20, -10, -5, 100])
    pct, active, _ = await daily_risk_tracker.get_current_risk_per_trade_pct(
        mock_session, user_id=None
    )
    assert pct == SMART_REDUCTION_3_LOSSES_PCT


# ─── Trades today count ───


async def test_trades_today_count_uses_utc_midnight() -> None:
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: 3))
    now = datetime(2026, 5, 11, 14, 30, tzinfo=UTC)
    n = await daily_risk_tracker.get_trades_today_count(
        mock_session, user_id=None, now_utc=now
    )
    assert n == 3


async def test_trades_today_count_empty() -> None:
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    n = await daily_risk_tracker.get_trades_today_count(
        mock_session, user_id=None, now_utc=datetime.now(UTC)
    )
    assert n == 0


# ─── Pause (Redis) ───


async def test_pause_and_is_paused_global() -> None:
    """Global pause round-trip."""
    # Önce temizle
    await redis_client.delete(REDIS_PAUSE_GLOBAL_KEY)

    paused_until = await daily_risk_tracker.pause(user_id=None, hours=1)
    assert paused_until > datetime.now(UTC)

    is_paused, until = await daily_risk_tracker.is_paused(user_id=None)
    assert is_paused is True
    assert until is not None

    # Temizle
    await daily_risk_tracker.unpause(user_id=None)


async def test_pause_per_user() -> None:
    user_id = uuid.uuid4()
    key = f"{REDIS_PAUSE_KEY_PREFIX}:{user_id}"
    await redis_client.delete(key)

    await daily_risk_tracker.pause(user_id=user_id, hours=2)
    is_paused, _ = await daily_risk_tracker.is_paused(user_id=user_id)
    assert is_paused is True

    # Başka user etkilenmez
    other_id = uuid.uuid4()
    is_paused_other, _ = await daily_risk_tracker.is_paused(user_id=other_id)
    assert is_paused_other is False

    await daily_risk_tracker.unpause(user_id=user_id)


async def test_pause_hours_clamped() -> None:
    """0/50 saat → 1/48'e clamp."""
    await daily_risk_tracker.unpause(user_id=None)

    until_low = await daily_risk_tracker.pause(user_id=None, hours=0)
    # En az 1 saat
    delta_low = (until_low - datetime.now(UTC)).total_seconds() / 3600
    assert 0.95 < delta_low < 1.05

    await daily_risk_tracker.unpause(user_id=None)
    until_high = await daily_risk_tracker.pause(user_id=None, hours=100)
    delta_high = (until_high - datetime.now(UTC)).total_seconds() / 3600
    assert 47.95 < delta_high < 48.05

    await daily_risk_tracker.unpause(user_id=None)


async def test_is_paused_no_key_returns_false() -> None:
    await daily_risk_tracker.unpause(user_id=None)
    is_paused, until = await daily_risk_tracker.is_paused(user_id=None)
    assert is_paused is False
    assert until is None


# ─── Daily status composite ───


async def test_get_status_empty_db_defaults() -> None:
    """Boş DB → default risk %2, can_open=True."""
    await daily_risk_tracker.unpause(user_id=None)

    mock_session = MagicMock()
    # consecutive losses query (rows)
    mock_session.execute = AsyncMock(side_effect=[
        MagicMock(all=lambda: []),  # consecutive losses
        MagicMock(scalar_one_or_none=lambda: 0),  # trades today
    ])
    now = datetime(2026, 5, 11, 14, 30, tzinfo=UTC)
    status = await daily_risk_tracker.get_status(
        mock_session, user_id=None, now_utc=now
    )
    assert status.current_risk_per_trade_pct == DEFAULT_RISK_PCT
    assert status.smart_reduction_active is False
    assert status.trades_today == 0
    assert status.trades_remaining == DAILY_MAX_TRADES
    assert status.daily_risk_used_pct == 0.0  # MVP placeholder
    assert status.daily_risk_remaining_pct == DAILY_MAX_RISK_PCT
    assert status.can_open_new_trade is True
    assert status.block_reason is None
    assert status.paused_until is None


async def test_get_status_blocked_by_max_trades() -> None:
    await daily_risk_tracker.unpause(user_id=None)

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=[
        MagicMock(all=lambda: []),
        MagicMock(scalar_one_or_none=lambda: DAILY_MAX_TRADES),
    ])
    status = await daily_risk_tracker.get_status(
        mock_session, user_id=None, now_utc=datetime.now(UTC)
    )
    assert status.can_open_new_trade is False
    assert status.block_reason is not None
    assert "Günlük max" in status.block_reason
    assert status.trades_remaining == 0


async def test_get_status_blocked_by_pause() -> None:
    """Pause aktif → can_open=False, block_reason 'Manuel pause'."""
    await daily_risk_tracker.pause(user_id=None, hours=1)

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=[
        MagicMock(all=lambda: []),
        MagicMock(scalar_one_or_none=lambda: 0),
    ])
    status = await daily_risk_tracker.get_status(
        mock_session, user_id=None, now_utc=datetime.now(UTC)
    )
    assert status.can_open_new_trade is False
    assert status.paused_until is not None
    assert status.block_reason is not None
    assert "Manuel pause" in status.block_reason

    await daily_risk_tracker.unpause(user_id=None)


# ─── Constants ───


def test_constants() -> None:
    assert DEFAULT_RISK_PCT == 2.0
    assert SMART_REDUCTION_2_LOSSES_PCT == 1.5
    assert SMART_REDUCTION_3_LOSSES_PCT == 1.0
    assert DAILY_MAX_TRADES == 5
    assert DAILY_MAX_RISK_PCT == 4.0
    assert PAUSE_DEFAULT_HOURS == 4
