"""Фикстуры интеграционных тестов.

Используют реальный Postgres с прогоном через **alembic upgrade head**
(а не ``Base.metadata.create_all``) — потому что nutrition-схема включает
partitioned table, pg_trgm extension, и PL/pgSQL trigger, которых нет в
декларативных моделях.

Тестовая БД создаётся отдельно от ``make dev`` — обычно это
``bioarchitect_test``. CI задаёт URL через ``DATABASE_URL`` env var,
локально в Docker — берём дефолтные dev-креды и `_test` суффикс.

Маркер: все тесты в ``tests/integration/`` помечены ``-m integration``.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Импортируем все модели — нужно для типизации в тестах. Сама схема
# поднимается через alembic, не через metadata.create_all.
import src.domains.consent.models  # noqa: F401
import src.domains.nutrition.models  # noqa: F401
import src.domains.users.models  # noqa: F401

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _test_db_url() -> str:
    """URL тестовой БД.

    Приоритет: ``TEST_DATABASE_URL`` → ``DATABASE_URL`` → fallback на
    докер-сетевой адрес ``postgres:5432`` с dev-кредами.
    """
    explicit = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    return (
        "postgresql+asyncpg://bioarchitect:change_me_locally"
        "@postgres:5432/bioarchitect_test"
    )


def _asyncpg_dsn(sa_url: str) -> str:
    """sqlalchemy URL → DSN для asyncpg.connect()."""
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", sa_url)


async def _reset_schema(dsn: str) -> None:
    conn = await asyncpg.connect(dsn=dsn)
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def _migrated_database() -> str:
    """Один раз на сессию: дроп схемы + alembic upgrade head.

    Schema reset идёт в одноразовом event-loop'е через asyncio.run (до
    того, как pytest-asyncio создаст свой). Миграции — в subprocess,
    чтобы не конфликтовать с asyncio.run внутри alembic env.py.
    """
    async_url = _test_db_url()

    asyncio.run(_reset_schema(_asyncpg_dsn(async_url)))

    env = {**os.environ, "DATABASE_URL": async_url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(_PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}"
        )
    return async_url


# Список таблиц для TRUNCATE между тестами. Расширять при добавлении
# новых доменов с мутируемыми таблицами.
_TRUNCATE_TABLES = (
    "food_logs",        # CASCADE снесёт при users; явно перечисляем для idempotency
    "food_aliases",
    "food_items",
    "consent_records",
    "user_profiles",
    "users",
)


@pytest_asyncio.fixture
async def db_engine(_migrated_database: str) -> AsyncGenerator[AsyncEngine, None]:
    """Function-scoped движок.

    Session-scoped не работает с ``asyncio_mode = "auto"`` в pytest-asyncio
    0.24+: разные тесты получают разные event loop'ы. Function-scoped
    дороже на ~50ms, но надёжно.
    """
    engine = create_async_engine(_migrated_database, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test session. После теста — TRUNCATE проектных таблиц."""
    sessionmaker = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with sessionmaker() as session:
        try:
            yield session
        finally:
            await session.rollback()

    async with sessionmaker() as cleanup:
        for tbl in _TRUNCATE_TABLES:
            await cleanup.execute(text(f"TRUNCATE TABLE {tbl} CASCADE"))
        await cleanup.commit()
