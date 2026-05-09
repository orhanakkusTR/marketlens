"""MarketLens FastAPI app — Adım 3: full middleware + exception handling + structured logging."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException

from app.core.config import settings
from app.core.exceptions import (
    MarketLensError,
    http_exception_handler,
    marketlens_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    AccessLogMiddleware,
    RequestIDMiddleware,
    limiter,
    rate_limit_exceeded_handler,
)
from app.api.v1 import auth as auth_v1
from app.api.v1 import confluence as confluence_v1
from app.api.v1 import indicators as indicators_v1
from app.api.v1 import macro as macro_v1
from app.db.session import engine

# Logging modül yüklenirken yapılandırılır — uvicorn başlamadan önce çalışsın diye.
configure_logging(
    level=settings.log_level,
    json_output=(settings.log_format == "json"),
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "app_starting",
        environment=settings.environment,
        debug=settings.debug,
        version="0.1.0",
    )
    yield
    logger.info("app_shutting_down")

    # Lazy import to avoid circular at module load
    from app.core.redis_client import close_redis
    from app.services.data_service import data_service
    from app.services.indicators.engine import indicator_engine

    await indicator_engine.close()
    await data_service.close()
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="MarketLens API",
    version="0.1.0",
    description="Kişisel kripto + emtia karar destek terminali",
    lifespan=lifespan,
)

# ─── Middleware ───
# Starlette: ilk eklenen = innermost. RequestID'yi en sona ekliyoruz (outermost) —
# `BaseHTTPMiddleware` her dispatch'i ayrı subtask'ta çalıştırıyor; iç middleware'de
# bind edilen contextvars dış middleware'e propagate olmaz, ancak SUBTASK'LAR PARENT
# CONTEXT'İ KALITIM YOLUYLA ALIR. Yani AccessLog'un context görmesi için RequestID
# onun parent task'ı olmalı — outermost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestIDMiddleware)

# ─── Rate limiting (slowapi) ───
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ─── Exception handler'lar ───
# MarketLensError ve subclass'ları (en spesifik önce)
app.add_exception_handler(MarketLensError, marketlens_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
# Fallback: handle edilmeyen tüm Exception'lar
app.add_exception_handler(Exception, unhandled_exception_handler)


# ─── Routers ───
app.include_router(auth_v1.router, prefix="/api/v1")
app.include_router(indicators_v1.router, prefix="/api/v1")
app.include_router(confluence_v1.router, prefix="/api/v1")
app.include_router(macro_v1.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "marketlens-backend",
        "version": "0.1.0",
        "environment": settings.environment,
    }
