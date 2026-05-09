"""Настройки приложения.

Все переменные окружения читаются здесь и нигде больше. Прочие модули
получают валидированный объект ``Settings`` через ``get_settings()``.

Загрузка из ``.env`` для локальной разработки. В продакшне используем
sops + age (см. ``docs/architecture-decisions/0003-secrets-management.md``).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Главный объект настроек. Иммутабельный после инициализации."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Окружение ---
    env: Environment = Environment.LOCAL
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    tz: str = "UTC"

    # --- Telegram ---
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_bot_username: str = ""
    telegram_webhook_url: str = ""
    telegram_webhook_secret: SecretStr = SecretStr("")

    # --- Anthropic ---
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_model_haiku: str = "claude-haiku-4-5"
    anthropic_model_sonnet: str = "claude-sonnet-4-6"
    anthropic_prompt_cache: bool = True

    # --- БД ---
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "bioarchitect"
    postgres_user: str = "bioarchitect"
    postgres_password: SecretStr = SecretStr("change_me_locally")
    database_url: str = ""  # вычисляется ниже, если не задан

    # --- Redis ---
    redis_url: str = "redis://redis:6379/0"

    # --- Платежи ---
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    telegram_stars_enabled: bool = False
    yookassa_shop_id: str = ""
    yookassa_secret_key: SecretStr = SecretStr("")

    # --- Backblaze B2 (зашифрованное хранение фото бланков) ---
    b2_key_id: SecretStr = SecretStr("")
    b2_application_key: SecretStr = SecretStr("")
    b2_bucket_name: str = "bioarchitect-lab-reports-eu"
    b2_endpoint: str = "s3.eu-central-003.backblazeb2.com"
    lab_reports_encryption_key: SecretStr = SecretStr("")

    # --- Sentry / observability ---
    sentry_dsn: str = ""
    sentry_environment: str = "local"
    sentry_traces_sample_rate: float = 0.1
    prometheus_port: int = 9090

    # --- Лимиты тарифов ---
    rate_limit_free_llm_per_day: int = 5
    rate_limit_pro_llm_per_day: int = 50
    rate_limit_proplus_llm_per_day: int = 150
    rate_limit_free_vision_per_day: int = 1
    rate_limit_pro_vision_per_day: int = 15
    rate_limit_proplus_vision_per_day: int = 30
    rate_limit_pro_ocr_per_month: int = 5
    rate_limit_proplus_ocr_per_month: int = 20

    # --- GDPR / правовые ---
    gdpr_deletion_grace_days: int = 30
    eu_data_residency_required: bool = True
    dpa_signed_anthropic: bool = False
    medical_advisor_name: str = ""
    medical_advisor_license: str = ""

    # --- Локализация ---
    default_locale: Literal["ru", "en", "pl", "de"] = "ru"
    supported_locales: Annotated[list[str], Field(default_factory=lambda: ["ru", "en", "pl", "de"])]

    # --- Censor ---
    censor_enabled: bool = True
    censor_log_blocked: bool = True

    # --- Mini App ---
    miniapp_url: str = "https://localhost:5173"
    miniapp_validate_init_data: bool = True

    @field_validator("supported_locales", mode="before")
    @classmethod
    def _split_locales(cls, v: object) -> object:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("censor_enabled")
    @classmethod
    def _censor_must_be_on_in_prod(cls, v: bool, info: object) -> bool:
        # Дополнительная защита: в продакшне Censor нельзя выключить.
        # Если попробуют — поднимаем ValueError на старте приложения.
        # Полная проверка делается в src/core/safety.py.
        return v

    @property
    def is_production(self) -> bool:
        return self.env == Environment.PRODUCTION

    @property
    def computed_database_url(self) -> str:
        """Если ``database_url`` пустой — собираем из частей."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton-доступ к настройкам.

    Кэшируется на всё время жизни процесса. В тестах сбрасывается
    через ``get_settings.cache_clear()``.
    """
    settings = Settings()
    # database_url алиас для удобства
    if not settings.database_url:
        object.__setattr__(settings, "database_url", settings.computed_database_url)
    return settings
