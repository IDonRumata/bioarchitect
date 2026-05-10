"""Enum-типы домена nutrition."""

from __future__ import annotations

from enum import StrEnum


class FoodSource(StrEnum):
    """Источник записи в food_items."""

    USDA = "usda"          # USDA FoodData Central (foundation foods)
    OFF = "off"            # Open Food Facts
    CHAIN = "chain"        # Chain Menu Database (Big Mac = 219g и т.д., спринт 5)
    MANUAL = "manual"      # Внесён вручную модератором / медэдвайзером


class FoodLogMethod(StrEnum):
    """Каким путём пользователь залогировал еду.

    Используется для аналитики (какой канал ввода работает лучше)
    и для формирования AI-контекста.
    """

    TEXT_INPUT = "text_input"      # «куриная грудка 200г»
    PHOTO_PHASE1 = "photo_phase1"  # распознавание по фото (спринт 4)
    PHOTO_PHASE2 = "photo_phase2"  # фото с эталоном (спринт 5, заглушка)
    CHAIN_MENU = "chain_menu"      # выбор из меню сети (спринт 5)
    QUICK_REPEAT = "quick_repeat"  # повтор последнего лога
