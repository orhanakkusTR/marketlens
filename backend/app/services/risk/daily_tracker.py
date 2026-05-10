"""Daily Risk Tracker — Adım 15.

Smart risk azaltma + günlük limit takibi + manuel pause.

DB read-only (trades tablosundan): consecutive losses, trades_today_count.
Redis: pause key (per-user veya global).

MVP not: daily_risk_used_pct şu an 0.0 placeholder. Trade tablosunda
adjusted_risk_pct kolonu yok — Adım 17'de Trade Journal entry sırasında
eklenir, o zaman gerçek hesap aktive olur.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.redis_client import redis_client
from app.models.trade import Trade
from app.schemas.risk import DailyRiskStatus

logger = get_logger(__name__)

TR_TZ = ZoneInfo("Europe/Istanbul")

DEFAULT_RISK_PCT = 2.0
SMART_REDUCTION_2_LOSSES_PCT = 1.5
SMART_REDUCTION_3_LOSSES_PCT = 1.0

DAILY_MAX_TRADES = 5
DAILY_MAX_RISK_PCT = 4.0

PAUSE_DEFAULT_HOURS = 4
PAUSE_MAX_HOURS = 48

REDIS_PAUSE_KEY_PREFIX = "marketlens:risk_pause"
REDIS_PAUSE_GLOBAL_KEY = f"{REDIS_PAUSE_KEY_PREFIX}:global"


def _pause_key(user_id: uuid.UUID | None) -> str:
    if user_id is None:
        return REDIS_PAUSE_GLOBAL_KEY
    return f"{REDIS_PAUSE_KEY_PREFIX}:{user_id}"


def _utc_midnight_today(now_utc: datetime) -> datetime:
    return now_utc.replace(hour=0, minute=0, second=0, microsecond=0)


def _format_paused_until(paused_until: datetime) -> str:
    tr = paused_until.astimezone(TR_TZ)
    return f"{paused_until:%H:%M} UTC / {tr:%H:%M} TR"


class DailyRiskTracker:
    """Public facade."""

    async def get_consecutive_losses(
        self, session: AsyncSession, user_id: uuid.UUID | None
    ) -> int:
        """Sondan başlayıp ardışık pnl<0 trade say. Closed trade'ler."""
        stmt = (
            select(Trade.pnl_usd)
            .where(Trade.status == "closed", Trade.exit_time.is_not(None))
            .order_by(Trade.exit_time.desc())
            .limit(20)
        )
        if user_id is not None:
            stmt = stmt.where(Trade.user_id == user_id)

        try:
            rows = (await session.execute(stmt)).all()
        except Exception as e:
            logger.warning("consecutive_losses_query_failed", error=str(e))
            return 0

        count = 0
        for row in rows:
            pnl = row[0]
            if pnl is None:
                break
            if float(pnl) < 0:
                count += 1
            else:
                break
        return count

    async def get_current_risk_per_trade_pct(
        self, session: AsyncSession, user_id: uuid.UUID | None
    ) -> tuple[float, bool, int]:
        """(risk_pct, smart_reduction_active, consecutive_losses)."""
        losses = await self.get_consecutive_losses(session, user_id)
        if losses >= 3:
            return SMART_REDUCTION_3_LOSSES_PCT, True, losses
        if losses >= 2:
            return SMART_REDUCTION_2_LOSSES_PCT, True, losses
        return DEFAULT_RISK_PCT, False, losses

    async def get_trades_today_count(
        self,
        session: AsyncSession,
        user_id: uuid.UUID | None,
        now_utc: datetime,
    ) -> int:
        """UTC midnight'tan beri açılan trade sayısı (closed + open)."""
        midnight = _utc_midnight_today(now_utc)
        stmt = (
            select(func.count(Trade.id))
            .where(Trade.entry_time >= midnight)
        )
        if user_id is not None:
            stmt = stmt.where(Trade.user_id == user_id)
        try:
            row = (await session.execute(stmt)).scalar_one_or_none()
        except Exception as e:
            logger.warning("trades_today_query_failed", error=str(e))
            return 0
        return int(row or 0)

    async def get_daily_risk_used_pct(
        self,
        session: AsyncSession,  # noqa: ARG002
        user_id: uuid.UUID | None,  # noqa: ARG002
        now_utc: datetime,  # noqa: ARG002
    ) -> float:
        """MVP: 0.0 placeholder.

        Trade tablosunda adjusted_risk_pct kolonu yok; Adım 17'de
        scenario engine + journal entry ile beraber eklenir.
        """
        return 0.0

    async def is_paused(
        self, user_id: uuid.UUID | None
    ) -> tuple[bool, datetime | None]:
        """Redis key kontrolü. TTL yoksa veya 0 → not paused."""
        key = _pause_key(user_id)
        try:
            value = await redis_client.get(key)
            if value is None:
                return False, None
            paused_until = datetime.fromisoformat(value)
            if paused_until.tzinfo is None:
                paused_until = paused_until.replace(tzinfo=UTC)
            if paused_until > datetime.now(UTC):
                return True, paused_until
            # Süresi geçmiş — temizle
            await redis_client.delete(key)
            return False, None
        except Exception as e:
            logger.warning("is_paused_failed", error=str(e))
            return False, None

    async def pause(
        self, user_id: uuid.UUID | None, hours: int
    ) -> datetime:
        """Pause aktive et — paused_until döner. Hours [1, 48] clamp'lenir."""
        hours = max(1, min(PAUSE_MAX_HOURS, hours))
        paused_until = datetime.now(UTC) + timedelta(hours=hours)
        key = _pause_key(user_id)
        try:
            await redis_client.set(
                key,
                paused_until.isoformat(),
                ex=hours * 3600,
            )
        except Exception as e:
            logger.warning("pause_set_failed", error=str(e))
        return paused_until

    async def unpause(self, user_id: uuid.UUID | None) -> None:
        """Manuel pause'u iptal et."""
        try:
            await redis_client.delete(_pause_key(user_id))
        except Exception as e:
            logger.warning("unpause_failed", error=str(e))

    async def get_status(
        self,
        session: AsyncSession,
        user_id: uuid.UUID | None,
        now_utc: datetime | None = None,
    ) -> DailyRiskStatus:
        if now_utc is None:
            now_utc = datetime.now(UTC)

        risk_pct, smart_active, losses = await self.get_current_risk_per_trade_pct(
            session, user_id
        )
        trades_today = await self.get_trades_today_count(session, user_id, now_utc)
        daily_used = await self.get_daily_risk_used_pct(session, user_id, now_utc)
        paused, paused_until = await self.is_paused(user_id)

        trades_remaining = max(0, DAILY_MAX_TRADES - trades_today)
        daily_remaining = max(0.0, DAILY_MAX_RISK_PCT - daily_used)

        # can_open_new_trade hierarchy
        can_open = True
        block_reason: str | None = None
        if paused and paused_until is not None:
            can_open = False
            block_reason = (
                f"Manuel pause aktif — {_format_paused_until(paused_until)}'a kadar."
            )
        elif trades_today >= DAILY_MAX_TRADES:
            can_open = False
            block_reason = (
                f"Günlük max {DAILY_MAX_TRADES} işlem hakkı doldu. "
                "Yarın UTC 00:00 (03:00 TR) sıfırlanır."
            )
        elif daily_used >= DAILY_MAX_RISK_PCT:
            can_open = False
            block_reason = (
                f"Günlük max risk %{DAILY_MAX_RISK_PCT} doldu. "
                "Yarın UTC 00:00 (03:00 TR) sıfırlanır."
            )

        return DailyRiskStatus(
            user_id=str(user_id) if user_id is not None else None,
            now_utc=now_utc,
            current_risk_per_trade_pct=risk_pct,
            smart_reduction_active=smart_active,
            consecutive_losses=losses,
            trades_today=trades_today,
            max_trades_per_day=DAILY_MAX_TRADES,
            trades_remaining=trades_remaining,
            daily_risk_used_pct=daily_used,
            daily_risk_max_pct=DAILY_MAX_RISK_PCT,
            daily_risk_remaining_pct=daily_remaining,
            paused_until=paused_until if paused else None,
            can_open_new_trade=can_open,
            block_reason=block_reason,
        )


daily_risk_tracker = DailyRiskTracker()
