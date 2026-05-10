"""Главное меню — Reply Keyboard для пользователя после онбординга.

ReplyKeyboardMarkup, не Inline — кнопки видны постоянно, не привязаны к
сообщению. Удобно для дальнобойщика за рулём в перерыве.
"""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Постоянно видимое меню с основными командами."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🍽 Еда"),
                KeyboardButton(text="💚 Самочувствие"),
            ],
            [
                KeyboardButton(text="⏱ Голодание"),
                KeyboardButton(text="📊 Сегодня"),
            ],
            [
                KeyboardButton(text="🧪 Анализы"),
                KeyboardButton(text="❓ Помощь"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="👤 Профиль"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Напиши «куриная грудка 200г» или пришли фото",
    )


def remove_main_menu() -> ReplyKeyboardRemove:
    """Убрать главное меню (используется при входе в FSM)."""
    return ReplyKeyboardRemove()
