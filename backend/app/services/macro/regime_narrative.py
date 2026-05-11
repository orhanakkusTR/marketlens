"""Rejim narrative üretici — Adım 20 polish v3.

İnsan dilinde Türkçe yorum: piyasa durumu + sistem analizi + risk faktörleri +
detaylı tavsiye. Şablon tabanlı; regime + setup_distribution + macro_summary +
zaman bağlamına göre branch'lenir.

Dış bağımlılık yok — saf transform fonksiyonu.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.macro import MarketRegime
from app.schemas.regime_detail import (
    DetailedAnalysisTr,
    RecommendationTr,
    RegimeMacroSummary,
    SetupDistribution,
)


# ─── Yardımcılar ───

def _fmt_pct(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def _fmt_signed(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{decimals}f}"


def _is_weekend_now(now: datetime) -> bool:
    """Cuma 22:00 UTC – Pzt 02:00 UTC arası."""
    day = now.weekday()
    hour = now.hour
    return (
        (day == 4 and hour >= 22)
        or day == 5
        or day == 6
        or (day == 0 and hour < 2)
    )


def _is_weekend_approaching(now: datetime) -> int | None:
    """Cuma 14:00–22:00 UTC arası → saat döner; aksi → None."""
    if now.weekday() == 4 and 14 <= now.hour < 22:
        return 22 - now.hour
    return None


# ─── 1. market_state ───

def _market_state(
    regime: MarketRegime, macro: RegimeMacroSummary
) -> str:
    btc_trend = macro.btc_trend_7d_pct
    eth_btc = macro.eth_btc_change_pct
    btc_d = macro.btc_dominance
    fg = macro.fear_greed_value
    fg_label = macro.fear_greed_label_tr

    if regime == "BTC_BULL":
        return (
            f"Piyasa BTC öncülüğünde yükselişte. BTC son 7 günde "
            f"{_fmt_pct(btc_trend, 1)} kazandı ve BTC.D %{btc_d:.1f} "
            f"seviyesinde — sermaye BTC'ye akıyor. Altcoinler henüz "
            f"harekete geçmemiş olabilir."
        )

    if regime == "ALT_BULL":
        return (
            f"Altseason aktif. BTC.D %{btc_d:.1f} ve ETH/BTC "
            f"{_fmt_pct(eth_btc, 2)} (7g). Altcoinlere sermaye akıyor, "
            f"fırsatlar bol olabilir. F&G {fg} {fg_label} — piyasa "
            f"genel olarak risk iştahında."
        )

    if regime == "ALT_SEASON_EARLY":
        return (
            f"Altcoinler ısınmaya başlıyor. ETH/BTC {_fmt_pct(eth_btc, 2)} "
            f"(7g) ile pozitife dönüş sinyali veriyor. BTC.D %{btc_d:.1f} "
            f"— henüz tam altseason değil ama erken sinyaller var. "
            f"Seçici altcoin pozisyonları değerlendirilebilir."
        )

    if regime == "RISK_OFF":
        return (
            f"Risk-off ortam — genel kripto satışı var. BTC son 7 günde "
            f"{_fmt_pct(btc_trend, 1)} ve F&G {fg} ({fg_label}). Sermaye "
            f"koruması öncelikli olmalı, yeni pozisyon açmak yerine "
            f"mevcutları yönetmek mantıklı."
        )

    # MIXED — alt branch'ler
    if btc_trend is not None and btc_trend > 0:
        return (
            f"Şu anda piyasa hafif yükseliş eğiliminde ama momentum zayıf. "
            f"BTC son 7 günde {_fmt_pct(btc_trend, 1)} yükselmiş, fakat "
            f"altcoinler geride kalıyor (ETH/BTC {_fmt_pct(eth_btc, 2)}). "
            f"Bu durum altseason'ın henüz başlamadığını gösteriyor. F&G "
            f"{fg} {fg_label} — trader'lar kararsız."
        )
    if btc_trend is not None and btc_trend < 0:
        return (
            f"Piyasada belirsizlik var. BTC son 7 günde "
            f"{_fmt_pct(btc_trend, 1)} düşmüş ama panik satışı seviyesinde "
            f"değil. F&G {fg} {fg_label} — yön bulmak için biraz daha "
            f"veri gerekiyor."
        )
    return (
        f"Piyasa yön arıyor. F&G {fg} {fg_label} ve BTC.D %{btc_d:.1f} "
        f"— kararlı bir trend henüz oluşmamış. Veriler netleşene kadar "
        f"sabırlı olmak en güvenli yaklaşım."
    )


# ─── 2. system_state ───

def _system_state(distribution: SetupDistribution) -> str:
    g = distribution.grade_counts
    total = distribution.total_symbols
    a, b, c, d, dur, none = g.A, g.B, g.C, g.D, g.NO_TRADE, g.none

    # Çoğunluk DUR (>10) → öncelik
    if dur > 10:
        return (
            f"Sistem çoğu sembolde 'DUR' diyor ({dur}/{total} sembol). "
            f"Bu, piyasada genel olarak ters sinyallerin baskın olduğu "
            f"anlamına geliyor — short fırsatları aramak veya beklemek "
            f"daha mantıklı olabilir."
        )

    yeni_suffix = ""
    if none > 5:
        yeni_suffix = (
            f" Ayrıca {none} sembol için yeterli veri yok ('Yeni' veya "
            f"hesaplanamadı) — analiz güvenilir değil, bu sembollere dikkat."
        )

    if a == 0 and b == 0:
        return (
            f"{total} sembolün hiçbirinde A veya B kalite setup yok. "
            f"Bu fırsat azlığı anlamına geliyor — sistem ısrarla 'bekle' "
            f"diyor. {c} sembol C ve {d} sembol D kalitede — açılsa "
            f"bile küçük pozisyon mantıklı. {dur} sembol DUR — "
            f"counter-trend veya trade quality problemi var.{yeni_suffix}"
        )

    if a + b <= 2:
        return (
            f"Sistem {a} A ve {b} B kalite setup tespit etti — bunlar "
            f"bugünün en güçlü fırsatları. Normal pozisyon boyutuyla "
            f"değerlendirilebilir. Diğer {c + d} sembolde C-D kalite "
            f"setup var.{yeni_suffix}"
        )

    if a >= 3:
        return (
            f"Bugün {a} A kalite setup var — bu yüksek bir sayı, piyasa "
            f"fırsat dolu. Ancak sermayeni dağıtma — en güçlü 1-2 "
            f"setup'a odaklan. {b} B kalite, {c} C kalite ek opsiyon."
            f"{yeni_suffix}"
        )

    # 3+ B-setup but no A — orta bolluk
    return (
        f"Sistem {a} A ve {b} B kalite setup gösteriyor. Birkaç fırsat "
        f"var, ancak A-setup azlığı dikkat gerektiriyor — B-kalite "
        f"setup'larda macro destekli olanlara öncelik verin.{yeni_suffix}"
    )


# ─── 3. risk_factors (warnings'in detaylı versiyonu + ek faktörler) ───

def _risk_factors(
    macro: RegimeMacroSummary, now: datetime
) -> list[str]:
    factors: list[str] = []

    # BTC.D
    btc_d = macro.btc_dominance
    if btc_d > 60:
        factors.append(
            f"BTC.D %{btc_d:.1f} yüksek seviyede → altcoinler baskı "
            f"altında, BTC tek güçlü olabilir"
        )
    elif btc_d < 50:
        factors.append(
            f"BTC.D %{btc_d:.1f} düşük → altcoinlere sermaye akışı "
            f"potansiyeli var"
        )

    # F&G
    fg = macro.fear_greed_value
    fg_label = macro.fear_greed_label_tr
    if fg < 25:
        factors.append(
            f"F&G {fg} ({fg_label}) → contrarian fırsat olabilir ama "
            f"timing önemli, dip yakalamak zor"
        )
    elif fg > 75:
        factors.append(
            f"F&G {fg} ({fg_label}) → düzeltme riski yüksek, fiyat "
            f"yorgunluğu olabilir"
        )
    elif 45 <= fg <= 55:
        factors.append(
            f"F&G {fg} ({fg_label}) → trader'lar kararsız, net yön yok"
        )

    # ETH/BTC
    eth_btc = macro.eth_btc_change_pct
    if eth_btc is not None:
        if eth_btc < -1:
            factors.append(
                f"ETH/BTC {_fmt_pct(eth_btc, 2)} (7g) → altcoinler "
                f"BTC'den daha zayıf, alt-pozisyonlarda dikkat"
            )
        elif eth_btc > 2:
            factors.append(
                f"ETH/BTC {_fmt_pct(eth_btc, 2)} (7g) → altcoinler "
                f"BTC'den güçlü, alt-rotasyon potansiyeli"
            )

    # TradFi
    if macro.tradfi_signal == "bearish":
        factors.append(
            "TradFi bearish → macro engel (DXY/VIX yukarı, SP500 aşağı), "
            "kripto'ya baskı"
        )
    elif macro.tradfi_signal == "bullish":
        factors.append(
            "TradFi bullish → macro destek (DXY/VIX aşağı, SP500 yukarı), "
            "kripto için rüzgâr arkadan"
        )

    # Weekend
    if _is_weekend_now(now):
        factors.append(
            "Hafta sonu aktif → düşük likidite, manipülasyon ve gap "
            "riski yüksek"
        )
    else:
        hours_left = _is_weekend_approaching(now)
        if hours_left is not None:
            factors.append(
                f"Hafta sonu yaklaşıyor (~{hours_left} saat) → kripto'da "
                f"likidite düşer, gap riski artar. Pazartesi açılışına dikkat"
            )

    return factors[:5]


# ─── 4. recommendation (strategy_tr'nin detaylı versiyonu) ───

def _recommendation(
    regime: MarketRegime,
    distribution: SetupDistribution,
    macro: RegimeMacroSummary,
    now: datetime,
) -> RecommendationTr:
    g = distribution.grade_counts
    a_count = g.A
    weekend_active = _is_weekend_now(now)
    weekend_soon = _is_weekend_approaching(now) is not None
    weekend_any = weekend_active or weekend_soon

    if regime == "RISK_OFF":
        return RecommendationTr(
            summary=(
                "Risk-off ortamda öncelik sermaye koruması. Yeni long "
                "açmak yerine mevcut pozisyonları küçültün veya kapatın."
            ),
            bullets=[
                "Yeni long açmayın",
                "Mevcut long'larınızı küçültün veya kapatın",
                "Short fırsatlarına bakın (A-B kalite)",
                "Cash pozisyonda durarak fırsat bekleyin",
                "F&G ekstrem korkuya inerse contrarian uzun düşünün",
            ],
        )

    if regime == "ALT_BULL":
        return RecommendationTr(
            summary=(
                "Altseason aktif — fırsatlar bol. Altcoin long'larda "
                "agresif olabilirsiniz ama kapatma disiplini kritik."
            ),
            bullets=[
                "Altcoin long pozisyonlar agresif olabilir",
                "BTC.D düşüşünü takip edin (alt rotasyon teyidi)",
                "Sektör rotasyonuna dikkat (L1 → DeFi → meme)",
                "Pump'ları takip etmeyin, A-B setup'larda kalın",
                "F&G yüksekse → kapatma disiplini kritik",
            ],
        )

    if regime == "BTC_BULL":
        return RecommendationTr(
            summary=(
                "BTC öncülüğünde rally. BTC ve major'larda long açın, "
                "altcoinlerden kaçının veya küçük tutun."
            ),
            bullets=[
                "BTC ve major'larda (ETH, SOL, BNB) long",
                "Altcoinleri SATIN ya da minimal tutun",
                "TP'leri yukarı doğru kademeli koyun",
                "Trailing stop kullanın (kar kilitle)",
                "BTC.D yön değişimini izleyin (alt rotasyon sinyali)",
            ],
        )

    if regime == "ALT_SEASON_EARLY":
        return RecommendationTr(
            summary=(
                "Erken altseason — kademeli altcoin long, ihtiyatlı "
                "agresiflik. Tam onay için ETH/BTC ve BTC.D trendini izleyin."
            ),
            bullets=[
                "Seçili altcoin long, küçük başla (%1 risk)",
                "BTC.D trendini izleyin (düşüşse teyit)",
                "L1'lerden başla (SOL, BNB, AVAX), sonra L2/DeFi",
                "Meme pump'larına kapılmayın — sinyal değil noise",
            ],
        )

    # MIXED varyasyonları
    if a_count == 0:
        bullets = [
            "Pozisyon boyutunu yarıya indirin (%1 risk)",
            "TP1'de tam çıkış yapın (hızlı kar al)",
            "Stop'u sıkı tutun (ATR×1)",
        ]
        if weekend_any:
            bullets.append("Hafta sonu öncesi tüm pozisyonları kapatın")
        return RecommendationTr(
            summary=(
                "Bugün büyük pozisyon almak için uygun ortam değil. "
                "A veya B setup oluşana kadar bekleyin. Şu anki C-D "
                "setup'larda işlem yapacaksanız aşağıdaki disiplini koruyun:"
            ),
            bullets=bullets,
        )

    if a_count <= 2:
        return RecommendationTr(
            summary=(
                "Sistem A kalite fırsat tespit etti. Normal pozisyon "
                "boyutuyla değerlendirebilirsiniz, ama disiplin kritik."
            ),
            bullets=[
                "Confidence VERY_LOW (yeni başlangıç) → küçük başlayın",
                "Stop'unuza disiplinli olun (taşıma yok)",
                "Macro destekli setup'ları öncelikleyin",
                "Aynı anda 1-2 pozisyondan fazla açmayın",
            ],
        )

    # 3+ A-setup
    return RecommendationTr(
        summary=(
            "Birden fazla A kalite fırsat var, ama sermayeni dağıtma. "
            "En güçlü 1-2 setup'a odaklan."
        ),
        bullets=[
            "En yüksek skorlu 1-2 setup seç",
            "Sektör çeşitliliği koru (aynı sektörden 2+ açma)",
            "Toplam günlük risk %4'ü aşmasın",
            "Bir tanesi stop'a takılırsa diğerine geçme — gün sonu değerlendir",
        ],
    )


# ─── Public ───

def build_detailed_analysis(
    regime: MarketRegime,
    distribution: SetupDistribution,
    macro: RegimeMacroSummary,
    now: datetime | None = None,
) -> DetailedAnalysisTr:
    """Tüm narrative parçalarını üret."""
    if now is None:
        now = datetime.now(UTC)
    return DetailedAnalysisTr(
        market_state=_market_state(regime, macro),
        system_state=_system_state(distribution),
        risk_factors=_risk_factors(macro, now),
        recommendation=_recommendation(regime, distribution, macro, now),
    )
