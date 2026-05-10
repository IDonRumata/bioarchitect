"""Тесты Pydantic-валидации онбординг-payload."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domains.users.enums import LifestyleTag, Sex, WorkPattern
from src.domains.users.schemas import OnboardingPayload


@pytest.mark.unit
def test_valid_payload_passes() -> None:
    payload = OnboardingPayload(
        country_iso="PL",
        locale="ru",
        sex=Sex.MALE,
        birth_year=1985,
        height_cm=180,
        weight_kg=82.5,
        work_pattern=WorkPattern.LONG_HAUL,
        lifestyle_tags=[LifestyleTag.LOW_CARB, LifestyleTag.INTERMITTENT_FASTING],
    )
    assert payload.country_iso == "PL"
    assert payload.lifestyle_tags == [
        LifestyleTag.LOW_CARB,
        LifestyleTag.INTERMITTENT_FASTING,
    ]


@pytest.mark.unit
def test_country_iso_must_be_two_chars() -> None:
    with pytest.raises(ValidationError):
        OnboardingPayload(
            country_iso="POL",  # три буквы — не alpha-2
            locale="ru",
            sex=Sex.UNSPECIFIED,
            birth_year=1985,
            height_cm=180,
            weight_kg=80,
            work_pattern=WorkPattern.UNSPECIFIED,
        )


@pytest.mark.unit
def test_unsupported_locale_rejected() -> None:
    with pytest.raises(ValidationError):
        OnboardingPayload(
            country_iso="PL",
            locale="fr",  # не поддерживается
            sex=Sex.UNSPECIFIED,
            birth_year=1985,
            height_cm=180,
            weight_kg=80,
            work_pattern=WorkPattern.UNSPECIFIED,
        )


@pytest.mark.unit
def test_birth_year_out_of_range() -> None:
    with pytest.raises(ValidationError):
        OnboardingPayload(
            country_iso="PL",
            locale="ru",
            sex=Sex.UNSPECIFIED,
            birth_year=2020,  # моложе 18
            height_cm=180,
            weight_kg=80,
            work_pattern=WorkPattern.UNSPECIFIED,
        )


@pytest.mark.unit
def test_height_must_be_realistic() -> None:
    with pytest.raises(ValidationError):
        OnboardingPayload(
            country_iso="PL",
            locale="ru",
            sex=Sex.UNSPECIFIED,
            birth_year=1985,
            height_cm=50,  # слишком мало
            weight_kg=80,
            work_pattern=WorkPattern.UNSPECIFIED,
        )


@pytest.mark.unit
def test_weight_must_be_realistic() -> None:
    with pytest.raises(ValidationError):
        OnboardingPayload(
            country_iso="PL",
            locale="ru",
            sex=Sex.UNSPECIFIED,
            birth_year=1985,
            height_cm=180,
            weight_kg=400,  # слишком много
            work_pattern=WorkPattern.UNSPECIFIED,
        )


@pytest.mark.unit
def test_extra_fields_forbidden() -> None:
    """``extra="forbid"`` — никаких лишних полей в payload."""
    with pytest.raises(ValidationError):
        OnboardingPayload(
            country_iso="PL",
            locale="ru",
            sex=Sex.UNSPECIFIED,
            birth_year=1985,
            height_cm=180,
            weight_kg=80,
            work_pattern=WorkPattern.UNSPECIFIED,
            unknown_field="injected",  # type: ignore[call-arg]
        )
