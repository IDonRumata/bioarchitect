"""Pydantic-схемы для домена users.

Используются между bot/api ↔ service. Не путать с SQLAlchemy-моделями.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.domains.users.enums import LifestyleTag, Sex, WorkPattern


class OnboardingPayload(BaseModel):
    """Финальный payload, собранный FSM-онбордингом."""

    model_config = ConfigDict(extra="forbid")

    country_iso: str = Field(..., min_length=2, max_length=2)
    locale: str = Field(..., pattern=r"^(ru|en|pl|de)$")
    sex: Sex
    birth_year: int = Field(..., ge=1900, le=2008)
    height_cm: int = Field(..., ge=100, le=250)
    weight_kg: float = Field(..., ge=30.0, le=300.0)
    work_pattern: WorkPattern
    lifestyle_tags: list[LifestyleTag] = Field(default_factory=list)


class UserSnapshot(BaseModel):
    """Read-only представление пользователя для UI."""

    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    username: str | None
    country_iso: str | None
    locale: str
    timezone: str
    onboarding_completed: bool
