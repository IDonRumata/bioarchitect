"""Inline-клавиатуры экрана /settings."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

LOCALE_LABELS: dict[str, str] = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "pl": "🇵🇱 Polski",
    "de": "🇩🇪 Deutsch",
}


def settings_root_keyboard(current_locale: str) -> InlineKeyboardMarkup:
    """Корневой экран настроек."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"🌐 Язык: {LOCALE_LABELS.get(current_locale, current_locale)}",
        callback_data="settings:locale",
    )
    builder.button(text="🗑 Удалить аккаунт", callback_data="settings:delete")
    builder.button(text="◀️ Закрыть", callback_data="settings:close")
    builder.adjust(1)
    return builder.as_markup()


def locale_picker_keyboard(current_locale: str) -> InlineKeyboardMarkup:
    """Выбор языка интерфейса."""
    builder = InlineKeyboardBuilder()
    for code, label in LOCALE_LABELS.items():
        marker = "✅ " if code == current_locale else ""
        builder.button(
            text=f"{marker}{label}",
            callback_data=f"settings:locale:{code}",
        )
    builder.button(text="◀️ Назад", callback_data="settings:back")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def delete_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Двойное подтверждение запроса удаления (GDPR)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Удалить мои данные через 30 дней",
                    callback_data="delete:confirm",
                )
            ],
            [
                InlineKeyboardButton(text="◀️ Отмена", callback_data="delete:cancel"),
            ],
        ]
    )


def deletion_undo_keyboard() -> InlineKeyboardMarkup:
    """Кнопка отмены удаления (доступна в течение grace period)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="↩️ Отменить удаление",
                    callback_data="delete:undo",
                )
            ]
        ]
    )
