"""Analysis Orchestrator unit testleri — graceful degradation + module statuses."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.analysis.orchestrator import (
    CoreAnalysisError,
    analysis_orchestrator,
)


async def test_phase1_indicators_fail_raises_core_error() -> None:
    """compute_all fail → CoreAnalysisError raise (caller 503'e çevirir)."""
    with patch(
        "app.services.analysis.orchestrator.indicator_engine.compute_all",
        new=AsyncMock(side_effect=Exception("binance down")),
    ):
        with pytest.raises(CoreAnalysisError):
            await analysis_orchestrator._compute_uncached(
                "BTCUSDT", "4H", session=None, user_id=None,
            )


async def test_phase1_final_confluence_fail_raises_core_error() -> None:
    """final_confluence fail → CoreAnalysisError raise."""
    with patch(
        "app.services.analysis.orchestrator.indicator_engine.compute_final_confluence",
        new=AsyncMock(side_effect=Exception("compute error")),
    ):
        with pytest.raises(CoreAnalysisError):
            await analysis_orchestrator._compute_uncached(
                "BTCUSDT", "4H", session=None, user_id=None,
            )


async def test_phase2_setup_quality_fail_raises_core_error() -> None:
    """setup_quality fail → CoreAnalysisError (zorunlu modül)."""
    with patch(
        "app.services.analysis.orchestrator._safe_setup_quality",
        new=AsyncMock(side_effect=Exception("sq down")),
    ):
        with pytest.raises(CoreAnalysisError):
            await analysis_orchestrator._compute_uncached(
                "BTCUSDT", "4H", session=None, user_id=None,
            )


@pytest.mark.integration
async def test_macro_fail_graceful_degradation() -> None:
    """Macro fail → response döner, macro=None, warning eklenir."""
    with patch(
        "app.services.analysis.orchestrator._safe_macro",
        new=AsyncMock(side_effect=Exception("macro api down")),
    ):
        result = await analysis_orchestrator._compute_uncached(
            "BTCUSDT", "4H", session=None, user_id=None,
        )
    assert result.macro is None
    macro_status = next(s for s in result.module_statuses if s.name == "macro")
    assert macro_status.ok is False
    assert "macro api down" in (macro_status.error or "")
    assert any("Macro" in w for w in result.warnings)


@pytest.mark.integration
async def test_correlations_fail_graceful_degradation() -> None:
    """Correlations fail → response döner, correlations=None."""
    with patch(
        "app.services.analysis.orchestrator._safe_correlations",
        new=AsyncMock(side_effect=Exception("correlation api down")),
    ):
        result = await analysis_orchestrator._compute_uncached(
            "BTCUSDT", "4H", session=None, user_id=None,
        )
    assert result.correlations is None
    corr_status = next(s for s in result.module_statuses if s.name == "correlations")
    assert corr_status.ok is False


@pytest.mark.integration
async def test_xauusdt_correlations_via_binance() -> None:
    """XAUUSDT artık Binance kline'da → correlations çalışmalı, hata vermemeli.

    Ocak 2026: TradFi Perpetual; eski Commodity-silent davranışı kaldırıldı.
    """
    from app.services.analysis.orchestrator import _safe_correlations

    result = await _safe_correlations("XAUUSDT")
    assert result.symbol == "XAUUSDT"
    # En az birkaç korelasyon olmalı (matrixteki diğer kriptolarla)
    assert len(result.all) > 0


def test_timings_class_measures_duration() -> None:
    """_Timed context manager basit duration ölçer."""
    import time

    from app.services.analysis.orchestrator import _Timed

    t = _Timed().__enter__()
    time.sleep(0.01)
    t.__exit__()
    assert t.duration_ms >= 9.0  # ~10ms beklenir, sleep imprecise
    assert t.duration_ms < 100.0
