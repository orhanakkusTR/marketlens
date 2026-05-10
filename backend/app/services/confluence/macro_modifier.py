"""Macro modifier hesabı — sembol tipine göre (btc / alt / commodity).

BTC.D historical yok (CoinGecko free) → primary "alt vs BTC" göstergesi ETH/BTC ratio:
- BTC için: ETH/BTC ↓ pozitif (BTC görece güçleniyor)
- ALT için: ETH/BTC ↑ pozitif (alts BTC'yi outperform ediyor)

Modifier toplamı clamp [-25, +25] (CLAUDE.md spec).
"""
from __future__ import annotations

from app.schemas.confluence import ModifierBreakdown, SymbolType
from app.schemas.macro import MacroSnapshot

MODIFIER_MIN = -25.0
MODIFIER_MAX = 25.0

REGIME_MODIFIER: dict[str, float] = {
    "ALT_BULL": 5.0,
    "ALT_SEASON_EARLY": 10.0,
    "BTC_BULL": -5.0,
    "RISK_OFF": -10.0,
    "MIXED": 0.0,
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def symbol_type(symbol: str) -> SymbolType:
    """26 USDT crypto + XAUUSDT (commodity) spec'i."""
    s = symbol.upper()
    if s == "BTCUSDT":
        return "btc"
    if s == "XAUUSDT":
        return "commodity"
    return "alt"


# ─── Helper formüller (her biri clamp ±10) ───


def _ethbtc_inverse_btc(eth_btc_7d_pct: float | None) -> float:
    """BTC için: ETH/BTC ↓ → BTC için pozitif (BTC.D ↑ proxy)."""
    if eth_btc_7d_pct is None:
        return 0.0
    return _clamp(-eth_btc_7d_pct * 2.0, -10, 10)


def _ethbtc_direct_alt(eth_btc_7d_pct: float | None) -> float:
    """ALT için: ETH/BTC ↑ → alts için pozitif."""
    if eth_btc_7d_pct is None:
        return 0.0
    return _clamp(eth_btc_7d_pct * 2.0, -10, 10)


def _sp500_modifier(sp500_7d_pct: float | None) -> float:
    """Risk-on göstergesi: SP500 ↑ → kripto için pozitif."""
    if sp500_7d_pct is None:
        return 0.0
    return _clamp(sp500_7d_pct * 1.5, -10, 10)


def _dxy_modifier_crypto(dxy_7d_pct: float | None) -> float:
    """DXY ↑ → kripto için negatif (negative correlation)."""
    if dxy_7d_pct is None:
        return 0.0
    return _clamp(-dxy_7d_pct * 2.0, -10, 10)


def _dxy_modifier_gold(dxy_7d_pct: float | None) -> float:
    """DXY ↓ → GOLD için pozitif (güçlü negative correlation)."""
    if dxy_7d_pct is None:
        return 0.0
    return _clamp(-dxy_7d_pct * 3.0, -15, 15)


def _vix_modifier_crypto(vix_level: float) -> float:
    """VIX seviyesine göre: <15 risk-on +5, >30 panik -10."""
    if vix_level < 15:
        return 5.0
    if vix_level <= 25:
        return 0.0
    if vix_level <= 30:
        return -5.0
    return -10.0


def _vix_modifier_gold(vix_level: float) -> float:
    """GOLD safe haven: VIX yüksek → GOLD pozitif."""
    if vix_level > 30:
        return 10.0
    if vix_level > 25:
        return 5.0
    if vix_level >= 15:
        return 0.0
    return -5.0


def _regime_modifier_alt(regime: str) -> float:
    """ALT için rejim-bazlı ek modifier."""
    return REGIME_MODIFIER.get(regime, 0.0)


# ─── Public API ───


def compute_macro_modifier(
    symbol: str, macro: MacroSnapshot
) -> tuple[float, ModifierBreakdown]:
    """Sembol için macro modifier ve component breakdown'ı dön.

    Toplam clamp [-25, +25].
    """
    s_type = symbol_type(symbol)

    ethbtc_7d = macro.eth_btc_ratio.change_7d_pct
    sp500_7d = macro.sp500.change_7d_pct
    dxy_7d = macro.dxy.change_7d_pct
    vix_level = macro.vix.current
    regime = macro.market_regime.regime

    if s_type == "btc":
        b_eth_btc = _ethbtc_inverse_btc(ethbtc_7d)
        b_sp500 = _sp500_modifier(sp500_7d)
        b_dxy = _dxy_modifier_crypto(dxy_7d)
        b_vix = _vix_modifier_crypto(vix_level)
        breakdown = ModifierBreakdown(
            eth_btc=b_eth_btc,
            sp500=b_sp500,
            dxy=b_dxy,
            vix=b_vix,
            regime=None,
            total3=None,
        )
        total = b_eth_btc + b_sp500 + b_dxy + b_vix

    elif s_type == "alt":
        b_eth_btc = _ethbtc_direct_alt(ethbtc_7d)
        b_sp500 = _sp500_modifier(sp500_7d)
        b_dxy = _dxy_modifier_crypto(dxy_7d) * 0.7  # ALT için BTC'nin %70'i
        b_vix = _vix_modifier_crypto(vix_level)
        b_regime = _regime_modifier_alt(regime)
        breakdown = ModifierBreakdown(
            eth_btc=b_eth_btc,
            sp500=b_sp500,
            dxy=b_dxy,
            vix=b_vix,
            regime=b_regime,
            total3=None,  # CoinGecko free history yok — şimdilik
        )
        total = b_eth_btc + b_sp500 + b_dxy + b_vix + b_regime

    else:  # commodity (GOLD)
        b_dxy = _dxy_modifier_gold(dxy_7d)
        b_vix = _vix_modifier_gold(vix_level)
        breakdown = ModifierBreakdown(
            eth_btc=None,
            sp500=None,
            dxy=b_dxy,
            vix=b_vix,
            regime=None,
            total3=None,
        )
        total = b_dxy + b_vix

    return _clamp(total, MODIFIER_MIN, MODIFIER_MAX), breakdown
