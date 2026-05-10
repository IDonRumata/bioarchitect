"""Репозиторий домена nutrition.

Только data access. Бизнес-логика — в service.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.nutrition.models import FoodAlias, FoodItem, FoodLog


class NutritionRepository:
    """Доступ к таблицам food_items / food_aliases / food_logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_food_item(self, food_item_id: UUID) -> FoodItem | None:
        return await self._session.get(FoodItem, food_item_id)

    async def search_by_alias(
        self,
        *,
        query: str,
        locale: str,
        limit: int = 5,
        min_similarity: float = 0.3,
    ) -> list[tuple[FoodItem, float]]:
        """Fuzzy-поиск через pg_trgm.

        Возвращает топ-N FoodItem-ов с similarity-score (0..1) на основе
        совпадения запроса с любым алиасом подходящего locale. Если
        несколько алиасов одного FoodItem совпали — берётся максимум.

        Требуется ``set_limit`` (или GUC pg_trgm.similarity_threshold)
        не выше ``min_similarity``; устанавливается per-statement через
        ``set_limit($1)``.
        """
        # pg_trgm similarity. Сравниваем lower(alias) с lower(query) —
        # GIN trgm индекс case-insensitive не из коробки, нормализуем сами.
        sim = func.similarity(func.lower(FoodAlias.alias), func.lower(query)).label("sim")

        # Подзапрос: для каждого food_item_id берём max(similarity) среди
        # его алиасов нужного locale.
        ranked = (
            select(
                FoodAlias.food_item_id.label("food_item_id"),
                func.max(sim).label("max_sim"),
            )
            .where(FoodAlias.locale == locale)
            .where(sim >= min_similarity)
            .group_by(FoodAlias.food_item_id)
            .subquery()
        )

        stmt = (
            select(FoodItem, ranked.c.max_sim)
            .join(ranked, ranked.c.food_item_id == FoodItem.id)
            # verified первыми, потом по similarity, потом по короткости имени.
            .order_by(
                FoodItem.verified.desc(),
                ranked.c.max_sim.desc(),
                func.length(FoodItem.name).asc(),
            )
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(item, float(score)) for item, score in result.all()]

    async def add_food_item(self, item: FoodItem) -> FoodItem:
        self._session.add(item)
        await self._session.flush()
        return item

    async def add_alias(self, alias: FoodAlias) -> FoodAlias:
        self._session.add(alias)
        await self._session.flush()
        return alias

    async def upsert_food_item(
        self,
        *,
        source: str,
        external_id: str,
        defaults: dict[str, object],
    ) -> tuple[FoodItem, bool]:
        """Idempotent upsert по (source, external_id). Используется сидингом.

        Возвращает (item, created). Если уже была — обновляем ключевые
        нутриенты (источники могут уточнять КБЖУ между релизами).
        """
        stmt = (
            select(FoodItem)
            .where(FoodItem.source == source)
            .where(FoodItem.external_id == external_id)
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            for k, v in defaults.items():
                setattr(existing, k, v)
            await self._session.flush()
            return existing, False

        item = FoodItem(source=source, external_id=external_id, **defaults)
        self._session.add(item)
        await self._session.flush()
        return item, True

    async def add_food_log(self, log: FoodLog) -> FoodLog:
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_logs_for_day(
        self,
        *,
        user_id: UUID,
        day_start_utc: datetime,
        day_end_utc: datetime,
    ) -> list[FoodLog]:
        stmt = (
            select(FoodLog)
            .where(FoodLog.user_id == user_id)
            .where(FoodLog.logged_at >= day_start_utc)
            .where(FoodLog.logged_at < day_end_utc)
            .order_by(FoodLog.logged_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def set_trgm_threshold(self, threshold: float) -> None:
        """Установить pg_trgm.similarity_threshold на сессию.

        Нужно вызвать ПЕРЕД search_by_alias, если используется оператор `%`
        (мы используем явный similarity() — но threshold всё равно полезен
        для других мест: `%` в WHERE).
        """
        await self._session.execute(text(f"SELECT set_limit({threshold:.2f})"))
