"""Inline-клавиатуры для потока Vision Phase 1."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.agents.vision_phase1 import RecognizedItem


def recognition_item_keyboard(item: RecognizedItem, item_index: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения одного распознанного продукта.

    callback_data:
        ``vis:ok:<idx>:<grams>``   — подтвердить с предложенным весом.
        ``vis:edit:<idx>``          — ввести граммы вручную.
        ``vis:skip:<idx>``          — пропустить этот продукт.
    """
    grams = item.grams_mid
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"✅ {item.name_ru} ({grams} г)",
                callback_data=f"vis:ok:{item_index}:{grams}",
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить граммы",
                callback_data=f"vis:edit:{item_index}",
            ),
            InlineKeyboardButton(
                text="❌ Пропустить",
                callback_data=f"vis:skip:{item_index}",
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def parse_ok_callback(data: str) -> tuple[int, int] | None:
    """``vis:ok:<idx>:<grams>`` → (idx, grams). None при ошибке."""
    parts = data.split(":")
    if len(parts) != 4 or parts[0] != "vis" or parts[1] != "ok":
        return None
    try:
        return int(parts[2]), int(parts[3])
    except ValueError:
        return None


def parse_edit_callback(data: str) -> int | None:
    """``vis:edit:<idx>`` → idx. None при ошибке."""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "vis" or parts[1] != "edit":
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


def parse_skip_callback(data: str) -> int | None:
    """``vis:skip:<idx>`` → idx. None при ошибке."""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "vis" or parts[1] != "skip":
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None
