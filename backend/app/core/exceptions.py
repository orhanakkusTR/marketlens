"""MarketLens custom exception hiyerarşisi + global FastAPI handler'lar.

Standart hata response formatı (api-endpoints.md spec):
    {
        "error": "<error_code>",
        "message": "<human readable>",
        "details": {...},
        "request_id": "<uuid>"
    }
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class MarketLensError(Exception):
    """Tüm uygulama hatalarının base sınıfı.

    Subclass'lar `status_code`, `error_code`, `default_message` override eder.
    """

    status_code: int = 500
    error_code: str = "internal_error"
    default_message: str = "Beklenmeyen sunucu hatası"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(MarketLensError):
    status_code = 404
    error_code = "not_found"
    default_message = "Kaynak bulunamadı"


class UnauthorizedError(MarketLensError):
    status_code = 401
    error_code = "unauthorized"
    default_message = "Kimlik doğrulaması gerekli"


class ForbiddenError(MarketLensError):
    status_code = 403
    error_code = "forbidden"
    default_message = "Bu işleme yetkiniz yok"


class ValidationError(MarketLensError):
    status_code = 422
    error_code = "validation_error"
    default_message = "Girdi doğrulaması başarısız"


class ConflictError(MarketLensError):
    status_code = 409
    error_code = "conflict"
    default_message = "Çakışma"


class RateLimitError(MarketLensError):
    status_code = 429
    error_code = "rate_limit_exceeded"
    default_message = "Çok fazla istek"


# ─── Handler helpers ───


def _build_response(
    *,
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_code,
            "message": message,
            "details": details or {},
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ─── Handler'lar (main.py kayıt eder) ───


async def marketlens_exception_handler(
    request: Request, exc: MarketLensError
) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error(
            "marketlens_error",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            exc_info=exc,
        )
    else:
        logger.info(
            "marketlens_error",
            error_code=exc.error_code,
            status_code=exc.status_code,
            message=exc.message,
        )
    return _build_response(
        request=request,
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic body/query/path validasyon hataları."""
    return _build_response(
        request=request,
        status_code=422,
        error_code="validation_error",
        message="Girdi doğrulaması başarısız",
        details={"errors": exc.errors()},
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """FastAPI'nin kendi HTTPException'ları (örn. 404 bilinmeyen route)."""
    return _build_response(
        request=request,
        status_code=exc.status_code,
        error_code=f"http_{exc.status_code}",
        message=str(exc.detail),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Hiçbir handler yakalamazsa: 500 + log + sızıntı yok."""
    logger.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
    )
    return _build_response(
        request=request,
        status_code=500,
        error_code="internal_error",
        message="Beklenmeyen sunucu hatası",
    )
