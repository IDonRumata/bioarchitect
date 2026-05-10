"""Бизнес-логика согласий."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.consent.enums import ConsentType
from src.domains.consent.models import ConsentRecord
from src.domains.consent.repository import ConsentRepository

# Версии документов согласий. При изменении — bumpим, и старые становятся stale.
CONSENT_VERSIONS: dict[ConsentType, str] = {
    ConsentType.TERMS_OF_SERVICE: "1.0",
    ConsentType.HEALTH_DATA_PROCESSING: "1.0",
    ConsentType.ANALYTICS: "1.0",
    ConsentType.MARKETING: "1.0",
    ConsentType.LAB_REPORT_STORAGE: "1.0",
}

# Соль для хеширования IP. В продакшне — берётся из секрета.
_IP_HASH_SALT = "bioarchitect-static-fallback"


class ConsentService:
    """Append-only управление согласиями."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ConsentRepository(session)

    async def grant(
        self,
        *,
        user_id: UUID,
        consent_type: ConsentType,
        ip_address: str | None = None,
        user_agent: str | None = None,
        notes: str | None = None,
    ) -> ConsentRecord:
        """Зафиксировать согласие пользователя.

        ВАЖНО: всегда новая запись. Никаких UPDATE существующих строк.
        """
        record = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            version=CONSENT_VERSIONS[consent_type],
            granted=True,
            granted_at=datetime.now(UTC),
            ip_hash=_hash_ip(ip_address) if ip_address else None,
            user_agent=user_agent[:256] if user_agent else None,
            notes=notes,
        )
        return await self._repo.add(record)

    async def revoke(
        self,
        *,
        user_id: UUID,
        consent_type: ConsentType,
        notes: str | None = None,
    ) -> ConsentRecord:
        """Отзыв согласия — новая запись с granted=False."""
        record = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            version=CONSENT_VERSIONS[consent_type],
            granted=False,
            granted_at=datetime.now(UTC),
            notes=notes,
        )
        return await self._repo.add(record)

    async def has_active_consent(
        self,
        user_id: UUID,
        consent_type: ConsentType,
    ) -> bool:
        """Активно ли согласие пользователя на текущей версии документа."""
        latest = await self._repo.latest(user_id, consent_type)
        if latest is None:
            return False
        if not latest.granted:
            return False
        # Проверяем актуальность версии: если документ обновлён, согласие устарело.
        return latest.version == CONSENT_VERSIONS[consent_type]


def _hash_ip(ip: str) -> str:
    """SHA-256 хеш IP с солью. Полный IP в БД не хранится."""
    return hashlib.sha256(f"{_IP_HASH_SALT}:{ip}".encode()).hexdigest()
