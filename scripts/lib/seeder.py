"""Общая логика идемпотентного сидинга food_items + food_aliases.

Каждый источник предоставляет нормализованные записи; этот модуль
переводит их в БД через ``NutritionRepository.upsert_food_item`` и
синхронизирует FoodAlias-ы.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.domains.nutrition.enums import FoodSource
from src.domains.nutrition.models import FoodAlias
from src.domains.nutrition.repository import NutritionRepository

log = get_logger(__name__)


@dataclass(frozen=True)
class SeedRecord:
    """Унифицированная запись, готовая к upsert.

    Любой источник (USDA / OFF / manual) приводится к ``SeedRecord``.
    """

    source: FoodSource
    external_id: str  # уникален внутри источника
    name: str
    kcal_100g: float
    protein_100g: float
    fat_100g: float
    carbs_100g: float
    fiber_100g: float | None
    serving_g: float | None
    brand: str | None
    verified: bool
    aliases: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class SeedStats:
    """Сводка по итогам прогона."""

    items_created: int = 0
    items_updated: int = 0
    aliases_created: int = 0
    aliases_skipped: int = 0


async def upsert_records(
    session: AsyncSession,
    records: list[SeedRecord],
    *,
    batch_size: int = 200,
) -> SeedStats:
    """Идемпотентный upsert списка записей.

    Делает плоские батчи по ``batch_size`` с промежуточным flush — снижает
    давление на память при загрузке тысяч строк.
    """
    repo = NutritionRepository(session)
    stats = SeedStats()

    for i in range(0, len(records), batch_size):
        chunk = records[i : i + batch_size]
        for rec in chunk:
            defaults: dict[str, Any] = {
                "name": rec.name,
                "brand": rec.brand,
                "kcal_100g": rec.kcal_100g,
                "protein_100g": rec.protein_100g,
                "fat_100g": rec.fat_100g,
                "carbs_100g": rec.carbs_100g,
                "fiber_100g": rec.fiber_100g,
                "serving_g": rec.serving_g,
                "verified": rec.verified,
            }
            item, created = await repo.upsert_food_item(
                source=rec.source.value,
                external_id=rec.external_id,
                defaults=defaults,
            )
            if created:
                stats.items_created += 1
            else:
                stats.items_updated += 1

            await _sync_aliases(
                session=session,
                food_item_id=item.id,
                wanted=rec.aliases,
                stats=stats,
            )

        await session.flush()

    return stats


async def _sync_aliases(
    *,
    session: AsyncSession,
    food_item_id: Any,
    wanted: dict[str, list[str]],
    stats: SeedStats,
) -> None:
    """Добавить недостающие алиасы. Существующие не трогаем (идемпотентность)."""
    existing_stmt = (
        select(FoodAlias.locale, FoodAlias.alias)
        .where(FoodAlias.food_item_id == food_item_id)
    )
    existing_rows = await session.execute(existing_stmt)
    existing: set[tuple[str, str]] = {(loc, al) for loc, al in existing_rows.all()}

    for locale, alias_list in wanted.items():
        if locale not in {"ru", "en", "pl", "de"}:
            continue
        for alias in alias_list:
            cleaned = alias.strip()
            if not cleaned:
                continue
            cleaned = cleaned[:256]
            key = (locale, cleaned)
            if key in existing:
                stats.aliases_skipped += 1
                continue
            session.add(
                FoodAlias(
                    food_item_id=food_item_id,
                    locale=locale,
                    alias=cleaned,
                )
            )
            existing.add(key)
            stats.aliases_created += 1
