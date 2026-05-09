"""Pydantic v2 Settings — tüm env değişkenleri tipli, .env'den otomatik okunur.

Singleton `settings` instance modül seviyesinde. Tüm uygulama burayı import eder.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # .env'de henüz kullanmadığımız (Coinglass vb.) anahtarlar hata vermesin
    )

    # ─── General ───
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # ─── Database ───
    database_url: str

    # ─── Redis / Celery ───
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # ─── JWT / Security ───
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30
    # kid header (rotasyon): aktif key id; gelecekte v2, v3... olur.
    jwt_kid: str = "v1"
    # Rotasyon grace period için: JWT_OLD_SECRETS='{"v0": "old_secret_value"}'
    # Pydantic Settings JSON'u otomatik dict[str, SecretStr]'e parse eder.
    jwt_old_secrets: dict[str, SecretStr] = Field(default_factory=dict)
    encryption_key: SecretStr | None = None

    # ─── Logging ───
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # ─── Cache TTL'leri (saniye) ───
    cache_ttl_kline_1m: int = 30
    cache_ttl_kline_5m: int = 120
    cache_ttl_kline_15m: int = 60
    cache_ttl_kline_1h: int = 600
    cache_ttl_kline_4h: int = 1800
    cache_ttl_kline_1d: int = 3600
    cache_ttl_funding: int = 60
    cache_ttl_oi: int = 60
    cache_ttl_orderbook: int = 5
    cache_ttl_fear_greed: int = 3600
    cache_ttl_macro: int = 300
    cache_ttl_liquidation: int = 30
    cache_ttl_news: int = 300
    cache_ttl_calendar: int = 43200

    # ─── Rate Limit (dakika başına) ───
    rate_limit_auth: int = 5
    rate_limit_analysis: int = 30
    rate_limit_scanner_manual: int = 5
    rate_limit_ai_chat: int = 20
    rate_limit_default: int = 60

    # ─── Risk Defaults (UserSettings için seed değerleri) ───
    default_account_balance: float = 3000
    default_risk_per_trade_pct: float = 2.0
    default_max_leverage: int = 10
    default_daily_max_trades: int = 5
    default_daily_max_risk_pct: float = 4.0
    default_auto_pause_after_losses: int = 3
    default_risk_after_2_losses_pct: float = 1.5
    default_risk_after_3_losses_pct: float = 1.0

    # ─── Scanner ───
    scanner_default_interval_minutes: int = 15
    scanner_max_parallel: int = 3
    scanner_default_min_quality: str = "B"

    # ─── External APIs (sonraki adımlarda kullanılacak) ───
    binance_api_key: str = ""
    binance_api_secret: SecretStr | None = None
    binance_spot_url: str = "https://api.binance.com"
    binance_futures_url: str = "https://fapi.binance.com"
    binance_ws_url: str = "wss://stream.binance.com:9443/ws"

    coingecko_api_key: str = ""
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"

    coinglass_api_key: SecretStr | None = None
    coinglass_base_url: str = "https://open-api-v3.coinglass.com"

    cryptopanic_api_key: SecretStr | None = None
    etherscan_api_key: SecretStr | None = None
    bscscan_api_key: SecretStr | None = None

    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    telegram_bot_token: SecretStr | None = None
    telegram_bot_username: str = ""

    sentry_dsn: SecretStr | None = None
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1


# Modül seviyesi singleton — tüm uygulama buradan import eder.
settings = Settings()  # type: ignore[call-arg]
