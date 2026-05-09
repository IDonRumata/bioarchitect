"""Safety-инварианты приложения.

Этот модуль вызывается при старте бота / API / воркера и проверяет, что
приложение в безопасной конфигурации. Падает с ``RuntimeError``, если нет.
"""

from __future__ import annotations

from src.core.config import Environment, get_settings


class SafetyViolationError(RuntimeError):
    """Критическое нарушение safety-инварианта. Стартовать нельзя."""


def assert_safe_to_start() -> None:
    """Проверяет жёсткие инварианты перед стартом приложения.

    Raises:
        SafetyViolationError: если хотя бы один инвариант нарушен.
    """
    settings = get_settings()
    violations: list[str] = []

    # 1. Censor Agent в продакшне обязан быть включён
    if settings.env == Environment.PRODUCTION and not settings.censor_enabled:
        violations.append(
            "CENSOR_ENABLED=false in production. Censor Agent cannot be disabled."
        )

    # 2. EU residency: если включён — БД и Redis не должны быть на не-EU хостах.
    #    На уровне settings.py мы это валидируем только для известных хостов.
    #    Полная проверка — в CI скрипте deployment.

    # 3. Anthropic DPA должен быть подписан до обработки health-данных в продакшне.
    if settings.env == Environment.PRODUCTION and not settings.dpa_signed_anthropic:
        violations.append(
            "DPA_SIGNED_ANTHROPIC=false in production. "
            "DPA with Anthropic is required before processing health data of EU users."
        )

    # 4. Sentry в продакшне обязателен (для отслеживания инцидентов с health-данными).
    if settings.env == Environment.PRODUCTION and not settings.sentry_dsn:
        violations.append("SENTRY_DSN is empty in production.")

    # 5. Telegram токен обязателен для бота.
    if not settings.telegram_bot_token.get_secret_value():
        violations.append("TELEGRAM_BOT_TOKEN is empty.")

    # 6. Anthropic API key обязателен.
    if not settings.anthropic_api_key.get_secret_value():
        violations.append("ANTHROPIC_API_KEY is empty.")

    if violations:
        msg = "Safety violations detected:\n" + "\n".join(f"  - {v}" for v in violations)
        raise SafetyViolationError(msg)
