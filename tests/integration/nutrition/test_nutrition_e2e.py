"""End-to-end интеграционные тесты nutrition (БД + сервис).

Покрывают:
    - fuzzy-поиск через pg_trgm (RU/EN, опечатки).
    - log_food: snapshot нутриентов в food_logs (не зависит от будущих
      правок food_items).
    - daily_totals: агрегаты за UTC-сутки.
    - Append-only trigger: UPDATE на food_logs выбрасывает исключение.
    - food_logs partitioning routing (insert падает в нужную партицию).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.nutrition.enums import FoodLogMethod, FoodSource
from src.domains.nutrition.models import FoodAlias, FoodItem
from src.domains.nutrition.schemas import FoodLogCreate
from src.domains.nutrition.service import NutritionError, NutritionService
from src.domains.users.enums import UserStatus
from src.domains.users.models import User


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> User:
    u = User(
        telegram_id=900_000_000 + int(uuid4().int % 1_000_000),
        username="test_user",
        locale="ru",
        status=UserStatus.ACTIVE,
        country_iso="PL",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def chicken_breast(db_session: AsyncSession) -> FoodItem:
    """Тестовый продукт с алиасами на RU/EN."""
    item = FoodItem(
        source=FoodSource.MANUAL,
        external_id=f"TEST-{uuid4().hex[:8]}",
        name="Chicken breast, raw",
        kcal_100g=165,
        protein_100g=31,
        fat_100g=3.6,
        carbs_100g=0,
        fiber_100g=0,
        verified=True,
    )
    db_session.add(item)
    await db_session.flush()
    db_session.add_all(
        [
            FoodAlias(food_item_id=item.id, locale="ru", alias="куриная грудка"),
            FoodAlias(food_item_id=item.id, locale="ru", alias="грудка курицы"),
            FoodAlias(food_item_id=item.id, locale="en", alias="chicken breast"),
        ]
    )
    await db_session.flush()
    return item


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_finds_exact_alias(
    db_session: AsyncSession,
    chicken_breast: FoodItem,
) -> None:
    nutrition = NutritionService(db_session)
    hits = await nutrition.search(query="куриная грудка", locale="ru", limit=5)

    assert len(hits) >= 1
    assert hits[0].food_item_id == chicken_breast.id
    assert hits[0].similarity >= 0.85
    assert hits[0].verified is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_handles_typos(
    db_session: AsyncSession,
    chicken_breast: FoodItem,
) -> None:
    """pg_trgm должен найти при опечатках («куринная груддка»)."""
    nutrition = NutritionService(db_session)
    hits = await nutrition.search(query="куринная груддка", locale="ru", limit=3)

    assert len(hits) >= 1
    assert hits[0].food_item_id == chicken_breast.id
    # similarity ниже точного, но всё ещё над порогом auto-log.
    assert 0.4 <= hits[0].similarity < 0.85


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_returns_empty_below_threshold(
    db_session: AsyncSession,
    chicken_breast: FoodItem,
) -> None:
    nutrition = NutritionService(db_session)
    hits = await nutrition.search(
        query="абсолютно_другое_название_xyz",
        locale="ru",
        min_similarity=0.5,
    )
    assert hits == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_log_food_snapshots_nutrients(
    db_session: AsyncSession,
    user: User,
    chicken_breast: FoodItem,
) -> None:
    """200г куриной грудки → 330 ккал / 62 белка (snapshot из food_items×2)."""
    nutrition = NutritionService(db_session)
    log = await nutrition.log_food(
        FoodLogCreate(
            user_id=user.id,
            food_item_id=chicken_breast.id,
            grams=200,
            method=FoodLogMethod.TEXT_INPUT,
            raw_input="куриная грудка 200г",
        )
    )
    await db_session.commit()

    assert log.kcal == pytest.approx(330)
    assert log.protein_g == pytest.approx(62)
    assert log.fat_g == pytest.approx(7.2)
    assert log.carbs_g == pytest.approx(0)
    assert log.method == FoodLogMethod.TEXT_INPUT
    assert log.raw_input == "куриная грудка 200г"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_log_food_routes_to_correct_partition(
    db_session: AsyncSession,
    user: User,
    chicken_breast: FoodItem,
) -> None:
    """Запись с logged_at=2026-05 должна попасть в food_logs_2026_05."""
    nutrition = NutritionService(db_session)
    log = await nutrition.log_food(
        FoodLogCreate(
            user_id=user.id,
            food_item_id=chicken_breast.id,
            grams=100,
            method=FoodLogMethod.TEXT_INPUT,
            logged_at=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
        )
    )
    await db_session.commit()

    row = await db_session.execute(
        text("SELECT tableoid::regclass::text FROM food_logs WHERE id = :id"),
        {"id": log.id},
    )
    partition = row.scalar_one()
    assert partition == "food_logs_2026_05"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_log_food_fails_for_unknown_item(
    db_session: AsyncSession,
    user: User,
) -> None:
    nutrition = NutritionService(db_session)
    with pytest.raises(NutritionError):
        await nutrition.log_food(
            FoodLogCreate(
                user_id=user.id,
                food_item_id=uuid4(),  # не существует
                grams=100,
                method=FoodLogMethod.TEXT_INPUT,
            )
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_food_logs_immutable(
    db_session: AsyncSession,
    user: User,
    chicken_breast: FoodItem,
) -> None:
    """UPDATE на food_logs должен падать через PL/pgSQL trigger."""
    nutrition = NutritionService(db_session)
    log = await nutrition.log_food(
        FoodLogCreate(
            user_id=user.id,
            food_item_id=chicken_breast.id,
            grams=100,
            method=FoodLogMethod.TEXT_INPUT,
        )
    )
    await db_session.commit()

    with pytest.raises(DBAPIError) as exc_info:
        await db_session.execute(
            text("UPDATE food_logs SET grams = 999 WHERE id = :id"),
            {"id": log.id},
        )
        await db_session.commit()
    assert "append-only" in str(exc_info.value).lower()
    await db_session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daily_totals_aggregates(
    db_session: AsyncSession,
    user: User,
    chicken_breast: FoodItem,
) -> None:
    """Два лога за один UTC-день → корректная сумма КБЖУ."""
    nutrition = NutritionService(db_session)
    day = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)

    await nutrition.log_food(
        FoodLogCreate(
            user_id=user.id,
            food_item_id=chicken_breast.id,
            grams=200,
            method=FoodLogMethod.TEXT_INPUT,
            logged_at=day.replace(hour=8),
        )
    )
    await nutrition.log_food(
        FoodLogCreate(
            user_id=user.id,
            food_item_id=chicken_breast.id,
            grams=150,
            method=FoodLogMethod.TEXT_INPUT,
            logged_at=day.replace(hour=18),
        )
    )
    await db_session.commit()

    totals = await nutrition.daily_totals(user_id=user.id, day=day)
    # 200г + 150г = 350г куриной грудки. 165 ккал / 100г → 577.5
    assert totals.entries_count == 2
    assert totals.kcal == pytest.approx(577.5)
    assert totals.protein_g == pytest.approx(108.5)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_falls_through_locales(
    db_session: AsyncSession,
    chicken_breast: FoodItem,
) -> None:
    """Если в RU нет совпадений — handler пробует EN. Здесь проверяем только
    что en-алиас находится при locale='en'.
    """
    nutrition = NutritionService(db_session)
    hits = await nutrition.search(query="chicken breast", locale="en", limit=3)
    assert len(hits) >= 1
    assert hits[0].food_item_id == chicken_breast.id
