"""Структурированные логи через structlog.

Все логи в JSON, готовы к отправке в Loki / Sentry. PII-фильтрация
делается в ``src/core/safety.py`` через add-processor.
"""

from __future__ import annotations

import logging
import sys

import structlog

from src.core.config import get_settings


def configure_logging() -> None:
    """Вызывается один раз при старте приложения (bot/api/worker)."""
    settings = get_settings()

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.env.value == "local":
        # Разработчику — цветной consoler renderer.
        shared_processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # Продакшн — JSON.
        shared_processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Перенаправляем stdlib logging в structlog
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level),
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Получить логгер. Импортируется в каждом модуле."""
    return structlog.get_logger(name)
