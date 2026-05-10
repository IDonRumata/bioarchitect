"""Бизнес-логика домена nutrition."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.nutrition.models import FoodLog
from src.domains.nutrition.repository import NutritionRepository
from src.domains.nutrition.schemas import (
    DailyNutritionTotals,
    FoodLogCreate,
    FoodSearchHit,
)


class NutritionError(RuntimeError):
    """Невозможно выполнить операцию nutrition (например, неизвестный food_item)."""


class NutritionService:
    """Поиск продуктов и логирование съеденного."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NutritionRepository(session)

    async def search(
        self,
        *,
        query: str,
        locale: str,
        limit: int = 5,
        min_similarity: float = 0.3,
    ) -> list[FoodSearchHit]:
        """Fuzzy-поиск по food_aliases.

        Возвращает упорядоченный список кандидатов с similarity-score.
        Пустой список = нет совпадений выше порога — handler покажет
        пользователю «не нашёл, добавим вручную?».
        """
        cleaned = query.strip()
        if not cleaned:
            return []

        rows = await self._repo.search_by_alias(
            query=cleaned,
            locale=locale,
            limit=limit,
            min_similarity=min_similarity,
        )
        return [
            FoodSearchHit(
                food_item_id=item.id,
                name=item.name,
                brand=item.brand,
                source=item.source,
                verified=item.verified,
                kcal_100g=item.kcal_100g,
                protein_100g=item.protein_100g,
                fat_100g=item.fat_100g,
                carbs_100g=item.carbs_100g,
                similarity=score,
            )
            for item, score in rows
        ]

    async def log_food(self, payload: FoodLogCreate) -> FoodLog:
        """Залогировать съеденное.

        КБЖУ — снапшот из food_items на момент логирования. Изменения в
        food_items не повлияют на старые логи.
        """
        item = await self._repo.get_food_item(payload.food_item_id)
        if item is None:
            raise NutritionError(
                f"food_item {payload.food_item_id} not found"
            )

        ratio = payload.grams / 100.0
        log = FoodLog(
            user_id=payload.user_id,
            food_item_id=item.id,
            grams=payload.grams,
            kcal=item.kcal_100g * ratio,
            protein_g=item.protein_100g * ratio,
            fat_g=item.fat_100g * ratio,
            carbs_g=item.carbs_100g * ratio,
            method=payload.method,
            raw_input=payload.raw_input,
            logged_at=payload.logged_at or datetime.now(UTC),
        )
        return await self._repo.add_food_log(log)

    async def daily_totals(
        self,
        *,
        user_id: UUID,
        day: datetime,
    ) -> DailyNutritionTotals:
        """Посчитать КБЖУ за сутки UTC, в которые попадает ``day``.

        Note:
            Локальные сутки пользователя считаются в спринте 5, когда
            подключим зону TZ из ``users.timezone`` к Recovery Index.
            Сейчас — UTC-сутки.
        """
        day_start = day.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        logs = await self._repo.list_logs_for_day(
            user_id=user_id,
            day_start_utc=day_start,
            day_end_utc=day_end,
        )
        totals = DailyNutritionTotals()
        for log in logs:
            totals.kcal += log.kcal
            totals.protein_g += log.protein_g
            totals.fat_g += log.fat_g
            totals.carbs_g += log.carbs_g
            totals.entries_count += 1
        return totals
