"""Pydantic-схемы домена nutrition.

Используются между bot/api ↔ service. Не путать с SQLAlchemy-моделями.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domains.nutrition.enums import FoodLogMethod, FoodSource


class ParsedFoodEntry(BaseModel):
    """Результат NLP-парсинга одной строки пользователя.

    Из текста «куриная грудка 200г, рис 150г» получается список таких
    объектов. ``query`` — сам текст продукта, ``grams`` — извлечённый вес.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=200)
    grams: float = Field(..., gt=0, le=5000)


class FoodSearchHit(BaseModel):
    """Кандидат из food_items, найденный по fuzzy-поиску."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    food_item_id: UUID
    name: str
    brand: str | None
    source: FoodSource
    verified: bool
    kcal_100g: float
    protein_100g: float
    fat_100g: float
    carbs_100g: float
    similarity: float = Field(..., ge=0.0, le=1.0)


class FoodLogCreate(BaseModel):
    """Команда «залогировать еду» (после того, как FoodItem уже выбран)."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    food_item_id: UUID
    grams: float = Field(..., gt=0, le=5000)
    method: FoodLogMethod
    raw_input: str | None = Field(default=None, max_length=512)
    logged_at: datetime | None = None  # default = now() в сервисе


class FoodLogSnapshot(BaseModel):
    """Read-only представление одной записи food_logs для UI."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    food_item_id: UUID
    grams: float
    kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    method: FoodLogMethod
    logged_at: datetime


class DailyNutritionTotals(BaseModel):
    """Агрегаты за сутки — для daily check-in и Recovery Index (спринт 5)."""

    model_config = ConfigDict(extra="forbid")

    kcal: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbs_g: float = 0.0
    entries_count: int = 0
