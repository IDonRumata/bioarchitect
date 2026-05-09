"""Vision Phase 2 — весовая оценка для каждого подтверждённого продукта.

Трёхуровневая система:
    1. Chain Menu Database (0% погрешность) — если определена сеть.
    2. Reference Object Detection (5-8%) — Faster R-CNN + MobileNetV3.
       ЗАГЛУШЕНО на MVP (см. ADR-0002), реализация в v2.0.
    3. Visual Range Estimate (резерв) — диапазон, requires_confirmation.

Output: ``WeightEstimate`` с обязательным полем ``source`` (no nulls).

Реализация — спринт 5.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WeightEstimate(BaseModel):
    """Оценка веса одной порции. ``source`` обязательно — null не допускается."""

    source: Literal["chain_menu", "reference_object", "visual_estimate", "user_input"]
    grams_min: int = Field(..., ge=0)
    grams_max: int = Field(..., ge=0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    needs_confirmation: bool

    def is_exact(self) -> bool:
        return self.grams_min == self.grams_max
