"""structlog yapılandırması — uvicorn/sqlalchemy stdlib logger'larını da JSON'a köprüler.

`request_id` `structlog.contextvars` üzerinden otomatik her log satırına enjekte edilir
(RequestIDMiddleware tarafından bind edilir).
"""
from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import Processor


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """structlog + stdlib logging entegrasyonu.

    Args:
        level: Root logger seviyesi (INFO/DEBUG vs.)
        json_output: True → JSONRenderer (her ortamda — proje tercihi).
            False → ConsoleRenderer (renkli, dev'de okunaklı). Tercih için bırakıldı.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # structlog ve stdlib logger'ların paylaştığı pre-chain
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # structlog'un kendi logger'ları için
    structlog.configure(
        processors=[
            *shared_processors,
            # Final processor: ProcessorFormatter'a hand off
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Renderer seçimi
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    # stdlib logger'larını da yakalayan formatter — uvicorn/sqlalchemy logları da JSON çıkar
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Gürültülü logger'ları sustur (SQL sorguları, her HTTP access log'u)
    for noisy in ("sqlalchemy.engine", "sqlalchemy.pool", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Modül-level logger helper.

    Kullanım:
        logger = get_logger(__name__)
        logger.info("event_name", key="value")
    """
    return structlog.stdlib.get_logger(name)
