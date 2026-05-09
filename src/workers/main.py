"""ARQ worker — точка входа для фоновых задач.

Запуск:
    arq src.workers.main.WorkerSettings

Задачи:
    - daily_checkin_reminders   — пуш в 21:00 локального времени
    - if_window_notifications   — старт/конец IF-окна
    - weekly_summary            — раз в неделю Coach Agent
    - chain_menu_quarterly_pull — обновление базы заправок (PDF-парсер)
    - churn_recovery            — re-engagement через 5 дней без активности
    - data_export_processor     — обработка GDPR-экспортов
    - data_deletion_processor   — hard delete после grace period
"""

from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from src.core.config import get_settings


async def startup(ctx: dict[str, Any]) -> None:
    """Инициализация воркера."""


async def shutdown(ctx: dict[str, Any]) -> None:
    """Очистка при остановке."""


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    """ARQ конфигурация. Подхватывается через ``arq <module>.WorkerSettings``."""

    functions: list[Any] = []  # будут заполняться по мере роста: спринты 5+
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
