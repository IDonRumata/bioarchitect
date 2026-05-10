"""Бизнес-логика домена users."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.consent.enums import ConsentType
from src.domains.consent.service import ConsentService
from src.domains.users.enums import UserStatus
from src.domains.users.models import User, UserProfile
from src.domains.users.repository import UserRepository
from src.domains.users.schemas import OnboardingPayload


class OnboardingError(RuntimeError):
    """Невозможно завершить онбординг (например, нет согласия Art. 9)."""


class UserService:
    """Регистрация, онбординг, удаление пользователя."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)
        self._consent = ConsentService(session)

    async def get_or_create(
        self,
        *,
        telegram_id: int,
        username: str | None,
        locale: str = "ru",
    ) -> tuple[User, bool]:
        """Найти пользователя по telegram_id или создать минимальную запись.

        Returns:
            (user, created) — флаг ``created`` = True, если пользователь новый.
        """
        existing = await self._repo.get_by_telegram_id(telegram_id)
        if existing is not None:
            # Тихо обновляем username — он может меняться в Telegram.
            if username is not None and existing.username != username:
                existing.username = username
            return existing, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            locale=locale,
            status=UserStatus.ACTIVE,
        )
        await self._repo.add(user)
        return user, True

    async def complete_onboarding(
        self,
        *,
        user: User,
        payload: OnboardingPayload,
    ) -> UserProfile:
        """Финализировать онбординг.

        Требования:
            - Пользователь уже дал ``HEALTH_DATA_PROCESSING`` согласие
              (GDPR Art. 9). Без него падаем с ``OnboardingError``.

        Создаёт ``UserProfile`` и ставит ``onboarding_completed_at`` на user.
        """
        if not await self._consent.has_active_consent(
            user.id,
            ConsentType.HEALTH_DATA_PROCESSING,
        ):
            raise OnboardingError(
                "GDPR Art. 9 health data consent is required before completing onboarding."
            )

        profile = UserProfile(
            user_id=user.id,
            sex=payload.sex,
            birth_year=payload.birth_year,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            work_pattern=payload.work_pattern,
            lifestyle_tags=[t.value for t in payload.lifestyle_tags],
        )
        await self._repo.add_profile(profile)

        user.country_iso = payload.country_iso
        user.locale = payload.locale
        user.onboarding_completed_at = datetime.now(UTC)
        return profile

    async def request_deletion(self, user: User) -> None:
        """Soft delete: ставит ``deletion_requested_at`` + status PENDING_DELETION.

        Hard delete — после grace period (30 дней) запускает ARQ-воркер
        ``data_deletion_processor`` (спринт 7+).
        """
        user.deletion_requested_at = datetime.now(UTC)
        user.status = UserStatus.PENDING_DELETION
