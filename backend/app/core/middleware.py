"""HTTP middleware'ler: RequestID, AccessLog, slowapi rate limiter."""
from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """X-Request-ID header'ı oku, yoksa uuid4 üret. structlog contextvars'a bind et.

    Bind edilen request_id sonraki tüm log satırlarında otomatik görünür
    (logging.py'deki structlog.contextvars.merge_contextvars sayesinde).
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(self.HEADER_NAME) or str(uuid.uuid4())

        # Her request için context temizle + request_id bind et
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self.HEADER_NAME] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Her request'i tek satır JSON log'la (request_id otomatik gelir)."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


# ─── Rate limiter (slowapi) ───
# Storage: in-memory (dev). Adım 5'te Redis client gelince storage_uri eklenir.

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_default}/minute"],
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """slowapi RateLimitExceeded → standart hata formatı."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Çok fazla istek (limit: {exc.detail})",
            "details": {"limit": str(exc.detail)},
            "request_id": getattr(request.state, "request_id", None),
        },
        headers={"Retry-After": "60"},
    )
