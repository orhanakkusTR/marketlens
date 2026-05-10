"""Analysis Orchestrator — Adım 17 (son backend adımı).

Tüm modülleri (indicators, confluence, alignment, setup_quality, macro,
correlations, risk_position) tek endpoint'te birleştirir.

Phase yapısı:
  Phase 1 (sequential, ZORUNLU — fail → 503):
    - indicators (compute_all, tüm modüller)
    - final_confluence

  Phase 2 (asyncio.gather, paralel — fail → graceful degradation):
    - setup_quality (içinde scenario + no_trade + confidence + counter_trend + trade_quality)
    - multi_tf_alignment
    - macro_snapshot
    - correlations (GOLD için None)

  Phase 3 (sequential — scenario'dan türetilir):
    - risk_position (compute_position; scenario None → None)

Cache: 30s TTL, user_id key'e gömülü (smart reduction user-specific).
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cached_call
from app.core.logging import get_logger
from app.data.binance_spot import TF_TO_INTERVAL
from app.db.session import AsyncSessionLocal
from app.schemas.analysis import (
    AnalysisFullResult,
    AnalysisModuleStatus,
    FetchTimings,
)
from app.schemas.confluence import AlignmentResult, FinalConfluenceResult
from app.schemas.correlation import SymbolCorrelations
from app.schemas.indicators import IndicatorBundle
from app.schemas.macro import MacroSnapshot
from app.schemas.risk import PositionRiskResult
from app.schemas.setup_quality import SetupQualityResult
from app.services.correlation.engine import correlation_engine
from app.services.indicators.engine import indicator_engine
from app.services.macro.context import macro_service
from app.services.quality.setup_quality import setup_quality_engine
from app.services.risk.daily_tracker import daily_risk_tracker
from app.services.risk.position_sizer import compute_position

logger = get_logger(__name__)

CACHE_TTL = 30


class CoreAnalysisError(Exception):
    """Phase 1 (indicators veya final_confluence) fail → caller 503'e çevirir."""


class _Timed:
    """Async context manager — duration_ms hesaplar."""

    def __init__(self) -> None:
        self.duration_ms: float = 0.0
        self._t0: float = 0.0

    def __enter__(self) -> "_Timed":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.duration_ms = (time.perf_counter() - self._t0) * 1000


def _fmt_btc_24h_change(klines: list[dict[str, Any]]) -> float | None:
    if len(klines) < 25:
        return None
    old = float(klines[0]["close"])
    new = float(klines[-1]["close"])
    if old <= 0:
        return None
    return ((new - old) / old) * 100


async def _safe_setup_quality(
    symbol: str, timeframe: str, session: AsyncSession, user_id: uuid.UUID | None
) -> SetupQualityResult:
    """Setup Quality zorunlu — direkt çağır, exception caller'a düşsün."""
    return await setup_quality_engine.evaluate(
        symbol, timeframe, session=session, user_id=user_id
    )


async def _safe_alignment(symbol: str) -> AlignmentResult:
    """Alignment fail olabilir ama core sayılır → setup_quality zaten kullanıyor."""
    return await indicator_engine.compute_multi_tf_alignment(symbol)


async def _safe_macro() -> MacroSnapshot:
    return await macro_service.get_snapshot()


async def _safe_correlations(symbol: str) -> SymbolCorrelations:
    """Tüm 27 sembol için correlation matrix'ten tek-sembol view.

    Ocak 2026 sonrası: XAUUSDT artık Binance kline'da → diğer sembollerle
    aynı pipeline'da. Eski "Commodity için sessiz None" mantığı kaldırıldı.
    """
    return await correlation_engine.get_symbol_correlations(symbol)


class AnalysisOrchestrator:
    """Public facade — tüm modülleri tek payload'da birleştirir."""

    async def compute_full_analysis(
        self,
        symbol: str,
        timeframe: str,
        *,
        session: AsyncSession | None = None,
        user_id: uuid.UUID | None = None,
    ) -> AnalysisFullResult:
        if timeframe not in TF_TO_INTERVAL:
            raise ValueError(f"Bilinmeyen timeframe: {timeframe}")

        user_key = str(user_id) if user_id is not None else "anonymous"
        cache_key = f"analysis:full:{symbol}:{timeframe}:{user_key}"

        async def _build() -> dict[str, Any]:
            result = await self._compute_uncached(symbol, timeframe, session, user_id)
            return result.model_dump(mode="json")

        # Cache hit kontrolü için önce direkt redis okuma yapmamız lazım
        # (cached_call helper var/yok bilgisini geri vermiyor)
        from app.core.cache import _full_key
        from app.core.redis_client import redis_client
        import json

        cache_hit = False
        try:
            raw = await redis_client.get(_full_key(cache_key))
            if raw is not None:
                cache_hit = True
                data = json.loads(raw)
                data["cache_hit"] = True
                return AnalysisFullResult.model_validate(data)
        except Exception as e:
            logger.warning("analysis_cache_read_failed", error=str(e))

        # Cache miss → tam compute
        result = await self._compute_uncached(symbol, timeframe, session, user_id)

        # Cache'e yaz
        try:
            await redis_client.set(
                _full_key(cache_key),
                json.dumps(result.model_dump(mode="json"), default=str),
                ex=CACHE_TTL,
            )
        except Exception as e:
            logger.warning("analysis_cache_write_failed", error=str(e))

        return result

    async def _compute_uncached(
        self,
        symbol: str,
        timeframe: str,
        session: AsyncSession | None,
        user_id: uuid.UUID | None,
    ) -> AnalysisFullResult:
        t_total = _Timed().__enter__()
        statuses: list[AnalysisModuleStatus] = []
        warnings: list[str] = []

        # ─── Phase 1: Core (sequential, zorunlu) ───
        phase1_t = _Timed().__enter__()
        try:
            bundle = await indicator_engine.compute_all(symbol, timeframe)
            statuses.append(
                AnalysisModuleStatus(name="indicators", ok=True)
            )
        except Exception as e:
            logger.error("phase1_indicators_failed", symbol=symbol, tf=timeframe, error=str(e))
            raise CoreAnalysisError(f"Indicators hesaplanamadı: {e}") from e

        try:
            final = await indicator_engine.compute_final_confluence(symbol, timeframe)
            statuses.append(
                AnalysisModuleStatus(name="final_confluence", ok=True)
            )
        except Exception as e:
            logger.error(
                "phase1_final_confluence_failed", symbol=symbol, tf=timeframe, error=str(e)
            )
            raise CoreAnalysisError(f"Final confluence hesaplanamadı: {e}") from e
        phase1_t.__exit__()

        current_price = (
            bundle.levels.current_price
            if bundle.levels is not None
            else (bundle.volatility.atr.value_usdt / (bundle.volatility.atr.value_pct / 100))
            if bundle.volatility is not None and bundle.volatility.atr.value_pct > 0
            else 0.0
        )

        # ─── Phase 2: Parallel (gather) ───
        # Session yönetimi: setup_quality DB kullanır
        local_session = session
        owned_session = False
        if local_session is None:
            local_session = AsyncSessionLocal()
            owned_session = True

        phase2_t = _Timed().__enter__()
        try:
            results = await asyncio.gather(
                _safe_setup_quality(symbol, timeframe, local_session, user_id),
                _safe_alignment(symbol),
                _safe_macro(),
                _safe_correlations(symbol),
                return_exceptions=True,
            )
        finally:
            if owned_session:
                await local_session.close()
        phase2_t.__exit__()

        sq_result, align_result, macro_result, corr_result = results

        # setup_quality — zorunlu
        if isinstance(sq_result, Exception):
            logger.error(
                "phase2_setup_quality_failed", symbol=symbol, tf=timeframe,
                error=str(sq_result),
            )
            raise CoreAnalysisError(f"Setup quality hesaplanamadı: {sq_result}") from sq_result
        statuses.append(AnalysisModuleStatus(name="setup_quality", ok=True))

        # alignment — zorunlu (setup_quality zaten kullanıyor, ama explicit field)
        if isinstance(align_result, Exception):
            logger.error(
                "phase2_alignment_failed", symbol=symbol, error=str(align_result),
            )
            raise CoreAnalysisError(
                f"Multi-TF alignment hesaplanamadı: {align_result}"
            ) from align_result
        statuses.append(AnalysisModuleStatus(name="multi_tf_alignment", ok=True))

        # macro — opsiyonel
        macro: MacroSnapshot | None
        if isinstance(macro_result, Exception):
            macro = None
            statuses.append(
                AnalysisModuleStatus(
                    name="macro", ok=False, error=str(macro_result)
                )
            )
            warnings.append("Macro verisi alınamadı — sembol analizi devam ediyor.")
            logger.warning("phase2_macro_failed", error=str(macro_result))
        else:
            macro = macro_result
            statuses.append(AnalysisModuleStatus(name="macro", ok=True))

        # correlations — opsiyonel (GOLD veya tek-sembol fail)
        correlations: SymbolCorrelations | None
        if isinstance(corr_result, Exception):
            correlations = None
            statuses.append(
                AnalysisModuleStatus(
                    name="correlations", ok=False, error=str(corr_result)
                )
            )
            warnings.append("Korelasyon verisi alınamadı.")
            logger.warning("phase2_correlations_failed", error=str(corr_result))
        else:
            correlations = corr_result
            statuses.append(AnalysisModuleStatus(name="correlations", ok=True))

        # ─── Phase 3: Risk position (scenario'dan türetilir) ───
        risk_position: PositionRiskResult | None = None
        phase3_t = _Timed().__enter__()
        try:
            scenario = sq_result.scenario
            if scenario is not None and bundle.volatility is not None:
                # Smart reduction sonrası risk yüzdesi
                # Phase 2 sonrası owned_session kapatıldı; yeni session aç (veya dış kullan)
                if session is not None:
                    risk_pct, _, _ = await daily_risk_tracker.get_current_risk_per_trade_pct(
                        session, user_id
                    )
                else:
                    async with AsyncSessionLocal() as risk_session:
                        risk_pct, _, _ = await daily_risk_tracker.get_current_risk_per_trade_pct(
                            risk_session, user_id
                        )

                funding_rate = (
                    bundle.futures.funding.current_rate
                    if bundle.futures is not None
                    else None
                )

                # BTC 24h proxy
                btc_change: float | None = None
                try:
                    btc_klines = await indicator_engine._get_klines("BTCUSDT", "1H", 25)
                    btc_change = _fmt_btc_24h_change(btc_klines)
                except Exception:
                    pass

                risk_position = compute_position(
                    symbol=symbol,
                    direction=scenario.direction,
                    balance=3000.0,
                    base_risk_pct=risk_pct,
                    entry=scenario.entry.mid,
                    stop=scenario.stop.price,
                    targets=[t.price for t in scenario.targets],
                    max_leverage=10,
                    funding_rate=funding_rate,
                    btc_24h_change_pct=btc_change,
                    atr_zscore=None,
                )
                statuses.append(
                    AnalysisModuleStatus(name="risk_position", ok=True)
                )
            else:
                statuses.append(
                    AnalysisModuleStatus(
                        name="risk_position",
                        ok=True,
                        error="Scenario yok (neutral direction veya yetersiz veri)",
                    )
                )
        except Exception as e:
            statuses.append(
                AnalysisModuleStatus(name="risk_position", ok=False, error=str(e))
            )
            warnings.append("Pozisyon hesabı yapılamadı.")
            logger.warning("phase3_risk_position_failed", error=str(e))
        phase3_t.__exit__()

        t_total.__exit__()

        # duration_ms'i her status'a ekleyemiyoruz (sequential ölçmedik) ama
        # phase'lerin toplam süresi fetch_timings'te var
        timings = FetchTimings(
            total_ms=t_total.duration_ms,
            phase1_core_ms=phase1_t.duration_ms,
            phase2_parallel_ms=phase2_t.duration_ms,
            phase3_risk_ms=phase3_t.duration_ms,
        )

        return AnalysisFullResult(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            computed_at=datetime.now(UTC),
            cache_hit=False,
            fetch_timings=timings,
            indicators=bundle,
            final_confluence=final,
            multi_tf_alignment=align_result,
            setup_quality=sq_result,
            macro=macro,
            correlations=correlations,
            risk_position=risk_position,
            module_statuses=statuses,
            warnings=warnings,
        )


analysis_orchestrator = AnalysisOrchestrator()
