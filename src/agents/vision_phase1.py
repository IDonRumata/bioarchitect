"""Vision Phase 1 — распознавание продуктов на фото.

Возвращает список ``RecognizedItem`` с confidence + alternatives.
Модель: Claude Sonnet 4.6 Vision.
Output: tool_use со строгой Pydantic-схемой (без свободного текста).

Реализация — спринт 4.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecognizedItem(BaseModel):
    """Один распознанный продукт на тарелке."""

    id: str
    name_en: str
    name_ru: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertain: bool
    alternatives: list[str] = Field(default_factory=list)


class Phase1Result(BaseModel):
    """Полный результат Phase 1."""

    items: list[RecognizedItem]
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    chain_brand_detected: str | None = None
