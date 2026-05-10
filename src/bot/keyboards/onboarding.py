"""Inline-клавиатуры онбординга."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.domains.users.enums import LifestyleTag, Sex, WorkPattern

# Топ-стран целевой аудитории. "Другая" — даёт ввод текстом.
TOP_COUNTRIES: list[tuple[str, str]] = [
    ("🇧🇾 Беларусь", "BY"),
    ("🇵🇱 Польша", "PL"),
    ("🇩🇪 Германия", "DE"),
    ("🇷🇺 Россия", "RU"),
    ("🇰🇿 Казахстан", "KZ"),
    ("🇺🇦 Украина", "UA"),
    ("🇱🇹 Литва", "LT"),
    ("🇱🇻 Латвия", "LV"),
    ("🇪🇪 Эстония", "EE"),
    ("🇨🇿 Чехия", "CZ"),
    ("🇸🇰 Словакия", "SK"),
    ("🇳🇱 Нидерланды", "NL"),
]


def gdpr_consent_keyboard() -> InlineKeyboardMarkup:
    """Кнопки согласия на обработку health-данных (GDPR Art. 9)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Соглашаюсь",
                    callback_data="onboard:gdpr:agree",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Не соглашаюсь",
                    callback_data="onboard:gdpr:decline",
                )
            ],
        ]
    )


def countries_keyboard() -> InlineKeyboardMarkup:
    """3 колонки кнопок со странами + 'другая'."""
    builder = InlineKeyboardBuilder()
    for label, code in TOP_COUNTRIES:
        builder.button(text=label, callback_data=f"onboard:country:{code}")
    builder.button(text="🌍 Другая (введу код)", callback_data="onboard:country:other")
    builder.adjust(3)
    return builder.as_markup()


def sex_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="♂ Мужской", callback_data=f"onboard:sex:{Sex.MALE.value}"),
                InlineKeyboardButton(text="♀ Женский", callback_data=f"onboard:sex:{Sex.FEMALE.value}"),
            ],
            [
                InlineKeyboardButton(
                    text="✦ Не указывать",
                    callback_data=f"onboard:sex:{Sex.UNSPECIFIED.value}",
                )
            ],
        ]
    )


def work_pattern_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚛 Дальние рейсы",
                    callback_data=f"onboard:work:{WorkPattern.LONG_HAUL.value}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⛏ Вахта",
                    callback_data=f"onboard:work:{WorkPattern.SHIFT_WORK.value}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 И то и то",
                    callback_data=f"onboard:work:{WorkPattern.MIXED.value}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💼 Офис",
                    callback_data=f"onboard:work:{WorkPattern.OFFICE.value}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✦ Пропустить",
                    callback_data=f"onboard:work:{WorkPattern.UNSPECIFIED.value}",
                )
            ],
        ]
    )


# Метки lifestyle-тегов
LIFESTYLE_TAG_LABELS: dict[LifestyleTag, str] = {
    LifestyleTag.LOW_CARB: "Низкоуглеводное",
    LifestyleTag.HORMONE_REPLACEMENT: "Заместительная терапия",
    LifestyleTag.INTERMITTENT_FASTING: "Практика голодания",
    LifestyleTag.VEGETARIAN: "Вегетарианство",
    LifestyleTag.VEGAN: "Веганство",
    LifestyleTag.HALAL: "Халяль",
    LifestyleTag.KOSHER: "Кошер",
    LifestyleTag.GLUTEN_FREE: "Без глютена",
    LifestyleTag.LACTOSE_FREE: "Без лактозы",
}


def lifestyle_tags_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Inline-клавиатура множественного выбора. Тогглит чекбоксы по callback'у."""
    builder = InlineKeyboardBuilder()
    for tag, label in LIFESTYLE_TAG_LABELS.items():
        mark = "✅" if tag.value in selected else "▫️"
        builder.button(
            text=f"{mark} {label}",
            callback_data=f"onboard:tag:{tag.value}",
        )
    builder.button(text="✓ Готово", callback_data="onboard:tags:done")
    builder.button(text="⤼ Пропустить", callback_data="onboard:tags:skip")
    builder.adjust(1)
    return builder.as_markup()
