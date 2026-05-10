"""Inline-клавиатуры для логирования еды."""

from __future__ import annotations

from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.domains.nutrition.schemas import FoodSearchHit


def food_choice_keyboard(
    hits: list[FoodSearchHit],
    *,
    grams: float,
    entry_index: int,
) -> InlineKeyboardMarkup:
    """Клавиатура с топ-N кандидатов + кнопка «не нашёл».

    callback_data:
        ``nut:pick:<entry_index>:<food_item_id>:<grams>`` — выбран кандидат.
        ``nut:skip:<entry_index>``                         — пропустить эту запись.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for hit in hits:
        label = _label(hit, grams)
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"nut:pick:{entry_index}:{hit.food_item_id}:{grams:g}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="✖ Пропустить",
                callback_data=f"nut:skip:{entry_index}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _label(hit: FoodSearchHit, grams: float) -> str:
    kcal = round(hit.kcal_100g * grams / 100)
    badge = "✓ " if hit.verified else ""
    name = hit.name if hit.brand is None else f"{hit.name} ({hit.brand})"
    if len(name) > 50:
        name = name[:47] + "…"
    return f"{badge}{name} — {kcal} ккал"


def parse_pick_callback(data: str) -> tuple[int, UUID, float] | None:
    """``nut:pick:<idx>:<uuid>:<grams>`` → (idx, uuid, grams). None при ошибке."""
    parts = data.split(":")
    if len(parts) != 5 or parts[0] != "nut" or parts[1] != "pick":
        return None
    try:
        idx = int(parts[2])
        food_item_id = UUID(parts[3])
        grams = float(parts[4])
    except ValueError:
        return None
    return idx, food_item_id, grams


def parse_skip_callback(data: str) -> int | None:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "nut" or parts[1] != "skip":
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None
