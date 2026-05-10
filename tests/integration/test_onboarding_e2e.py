"""End-to-end интеграционный тест: онбординг сервисного слоя.

Не использует aiogram — только UserService + ConsentService против реальной БД.
Проверяет инвариант: онбординг падает, если нет GDPR Art. 9 consent.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.consent.enums import ConsentType
from src.domains.consent.service import ConsentService
from src.domains.users.enums import LifestyleTag, Sex, UserStatus, WorkPattern
from src.domains.users.schemas import OnboardingPayload
from src.domains.users.service import OnboardingError, UserService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_onboarding_fails_without_health_consent(db_session: AsyncSession) -> None:
    user_service = UserService(db_session)
    user, created = await user_service.get_or_create(
        telegram_id=111111111,
        username="andrei",
    )
    assert created is True
    await db_session.commit()

    payload = OnboardingPayload(
        country_iso="PL",
        locale="ru",
        sex=Sex.MALE,
        birth_year=1985,
        height_cm=180,
        weight_kg=82.0,
        work_pattern=WorkPattern.LONG_HAUL,
        lifestyle_tags=[LifestyleTag.LOW_CARB],
    )

    with pytest.raises(OnboardingError):
        await user_service.complete_onboarding(user=user, payload=payload)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_onboarding_succeeds_with_consent(db_session: AsyncSession) -> None:
    user_service = UserService(db_session)
    consent_service = ConsentService(db_session)

    user, _ = await user_service.get_or_create(
        telegram_id=222222222,
        username="andrei2",
    )
    await db_session.flush()

    await consent_service.grant(
        user_id=user.id,
        consent_type=ConsentType.HEALTH_DATA_PROCESSING,
    )
    await db_session.flush()

    payload = OnboardingPayload(
        country_iso="DE",
        locale="de",
        sex=Sex.FEMALE,
        birth_year=1990,
        height_cm=168,
        weight_kg=62.5,
        work_pattern=WorkPattern.SHIFT_WORK,
        lifestyle_tags=[LifestyleTag.INTERMITTENT_FASTING, LifestyleTag.GLUTEN_FREE],
    )
    profile = await user_service.complete_onboarding(user=user, payload=payload)
    await db_session.commit()

    assert profile.user_id == user.id
    assert profile.height_cm == 168
    assert profile.work_pattern == WorkPattern.SHIFT_WORK
    assert "intermittent_fasting" in profile.lifestyle_tags
    assert "gluten_free" in profile.lifestyle_tags
    assert user.country_iso == "DE"
    assert user.locale == "de"
    assert user.onboarding_completed_at is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consent_revoke_makes_inactive(db_session: AsyncSession) -> None:
    user_service = UserService(db_session)
    consent_service = ConsentService(db_session)

    user, _ = await user_service.get_or_create(
        telegram_id=333333333,
        username="andrei3",
    )
    await db_session.flush()

    await consent_service.grant(
        user_id=user.id,
        consent_type=ConsentType.MARKETING,
    )
    assert await consent_service.has_active_consent(user.id, ConsentType.MARKETING)

    await consent_service.revoke(
        user_id=user.id,
        consent_type=ConsentType.MARKETING,
    )
    assert not await consent_service.has_active_consent(user.id, ConsentType.MARKETING)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_request_deletion_sets_status(db_session: AsyncSession) -> None:
    user_service = UserService(db_session)
    user, _ = await user_service.get_or_create(
        telegram_id=444444444,
        username="andrei4",
    )
    await db_session.flush()

    assert user.status == UserStatus.ACTIVE
    assert user.deletion_requested_at is None

    await user_service.request_deletion(user)

    assert user.status == UserStatus.PENDING_DELETION
    assert user.deletion_requested_at is not None
