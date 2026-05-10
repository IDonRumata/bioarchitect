"""Enum-типы домена users."""

from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    """Статус аккаунта пользователя."""

    ACTIVE = "active"
    SUSPENDED = "suspended"          # временная блокировка (антифлуд / абьюз)
    PENDING_DELETION = "pending_deletion"  # запрошено удаление, grace period 30 дней
    DELETED = "deleted"              # hard delete выполнен


class Sex(StrEnum):
    """Биологический пол. Используется для интерпретации лабораторных референсов.

    Не путать с гендерной идентичностью — это медицинский референс.
    Если пользователь не выбирает — используется ``UNSPECIFIED``, и
    референсы лабораторных значений показываются в комбинированном виде.
    """

    MALE = "male"
    FEMALE = "female"
    UNSPECIFIED = "unspecified"


class WorkPattern(StrEnum):
    """Тип работы — определяет адаптацию интерфейса (рейсы / вахта / офис)."""

    LONG_HAUL = "long_haul"          # дальние рейсы
    SHIFT_WORK = "shift_work"        # вахтовая работа
    MIXED = "mixed"                  # и то и то
    OFFICE = "office"                # офисный режим
    UNSPECIFIED = "unspecified"


class LifestyleTag(StrEnum):
    """Lifestyle-теги.

    ВАЖНО: это НЕ диагнозы. Это behavior / lifestyle preferences,
    которые пользователь сообщает о себе. Они подсказывают приложению
    контекст, но не являются медицинской информацией.

    Любые медицинские диагнозы → blacklist Censor Agent.
    """

    LOW_CARB = "low_carb"                       # низкоуглеводное питание
    HORMONE_REPLACEMENT = "hormone_replacement"  # заместительная терапия (ЗГТ/ТРТ)
    INTERMITTENT_FASTING = "intermittent_fasting"  # практика голодания
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HALAL = "halal"
    KOSHER = "kosher"
    GLUTEN_FREE = "gluten_free"
    LACTOSE_FREE = "lactose_free"
