"""Репозиторий домена consent. Append-only."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.consent.enums import ConsentType
from src.domains.consent.models import ConsentRecord


class ConsentRepository:
    """Доступ к ``consent_records``. Только INSERT и SELECT."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ConsentRecord) -> ConsentRecord:
        self._session.add(record)
        await self._session.flush()
        return record

    async def latest(
        self,
        user_id: UUID,
        consent_type: ConsentType,
    ) -> ConsentRecord | None:
        """Последняя запись согласия для (user, type)."""
        stmt = (
            select(ConsentRecord)
            .where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_type == consent_type,
            )
            .order_by(ConsentRecord.granted_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
