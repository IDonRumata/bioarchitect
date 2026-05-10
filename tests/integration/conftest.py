"""Фикстуры для интеграционных тестов.

Используют реальный Postgres (нужен ``DATABASE_URL`` env var). В CI это —
service container в .github/workflows/ci.yml. Локально — поднимается
через ``make dev`` и тесты бегут против той же БД (отдельная test_db).

Маркер: все тесты в ``tests/integration/`` помечены ``-m integration``.
В CI запускаются как часть ``test`` job, локально опускаются по умолчанию.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.db.base import Base

# Принудительно импортируем все модели, чтобы они зарегистрировались в metadata.
import src.domains.users.models  # noqa: F401
import src.domains.consent.models  # noqa: F401


def _test_db_url() -> str:
    """URL тестовой БД. CI задаёт DATABASE_URL, локально — fallback."""
    url = os.getenv("DATABASE_URL")
    if not url:
        # Fallback: локальная БД проекта (та же что в make dev)
        url = (
            "postgresql+asyncpg://bioarchitect:bioarchitect"
            "@localhost:5432/bioarchitect_test"
        )
    return url


@pytest_asyncio.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Один движок на всю тест-сессию."""
    engine = create_async_engine(_test_db_url(), echo=False, pool_pre_ping=True)
    async with engine.begin() as conn:
        # Чистая БД на каждый прогон.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Транзакционная фикстура: каждый тест в своей транзакции с rollback."""
    sessionmaker = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with sessionmaker() as session:
        # Нет savepoint logic — для простоты делаем rollback на сессии.
        # Каждый тест начинает с пустых таблиц по факту наличия CREATE/DROP в session-фикстуре.
        # Если нужны независимые тесты в одной сессии — переходим на savepoints.
        try:
            yield session
        finally:
            await session.rollback()
            # Очищаем таблицы между тестами (быстро для небольших объёмов).
            from sqlalchemy import text

            await session.execute(text("TRUNCATE users CASCADE"))
            await session.commit()


