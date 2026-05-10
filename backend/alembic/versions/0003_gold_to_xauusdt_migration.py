"""gold to xauusdt migration

XAUUSD (yfinance, USD quote, no futures) → XAUUSDT (Binance, USDT quote, futures).

Ocak 2026: Binance TradFi Perpetual Contracts başlattı; XAUUSDT artık Binance
Futures'ta mevcut. Bu sayede commodity sembolü diğer kriptolarla aynı pipeline'da
çalışır (kline, funding, OI, L/S, scenario, position).

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-11

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE marketlens.symbols
           SET code = 'XAUUSDT',
               quote_currency = 'USDT',
               exchange = 'binance',
               has_futures = true
         WHERE code = 'XAUUSD'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE marketlens.symbols
           SET code = 'XAUUSD',
               quote_currency = 'USD',
               exchange = 'yfinance',
               has_futures = false
         WHERE code = 'XAUUSDT'
        """
    )
