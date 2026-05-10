"""ARQ worker — точка входа для фоновых задач.

Запуск:
    arq src.workers.main.WorkerSettings

Задачи (по мере роста проекта):
    - data_deletion_processor    — hard-delete после 30 дней grace period (sprint 2)
    - daily_checkin_reminders    — пуш в 21:00 локального времени (sprint 5)
    - if_window_notifications    — старт/конец IF-окна (sprint 6)
    - weekly_summary             — раз в неделю Coach Agent (sprint 6)
    - chain_menu_quarterly_pull  — обновление базы заправок (PDF-парсер) (sprint 8)
    - churn_recovery             — re-engagement через 5 дней без активности (sprint 7)
    - data_export_processor      — обработка GDPR-экспортов (sprint 7)
"""

from __future__ import annotations

from typing import Any

from arq import cron
from arq.connections import RedisSettings

from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.workers.jobs.data_deletion import data_deletion_processor

log = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    log.info("worker.started")


async def shutdown(ctx: dict[str, Any]) -> None:
    log.info("worker.stopped")


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    """ARQ конфигурация. Запуск: ``arq src.workers.main.WorkerSettings``."""

    functions: list[Any] = [data_deletion_processor]

    cron_jobs = [
        # Каждый день в 03:00 UTC — hard-delete просроченных аккаунтов.
        cron(
            data_deletion_processor,
            name="data_deletion_processor",
            hour={3},
            minute={0},
            run_at_startup=False,
        ),
    ]

    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
