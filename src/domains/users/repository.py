"""Репозиторий домена users.

Только чистый data access (SELECT/INSERT/UPDATE). Бизнес-логика — в service.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domains.users.models import User, UserProfile


class UserRepository:
    """Доступ к таблицам users / user_profiles."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = (
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.profile))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def add_profile(self, profile: UserProfile) -> UserProfile:
        self._session.add(profile)
        await self._session.flush()
        return profile
