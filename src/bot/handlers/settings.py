"""``/settings`` — настройки пользователя.

В Спринте 2 — минимальный набор:
    - переключатель языка интерфейса
    - кнопка "Удалить аккаунт" (запускает /delete flow)

В Спринте 6+ добавим: часовой пояс, время daily check-in, частота
уведомлений, отключение рекламы для PRO, экспорт данных (GDPR).
"""

from __future__ import annotations

from typing import cast

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.settings import (
    LOCALE_LABELS,
    locale_picker_keyboard,
    settings_root_keyboard,
)
from src.core.config import get_settings
from src.core.i18n import set_locale
from src.domains.users.repository import UserRepository

router = Router(name="settings")


@router.message(Command("settings"))
@router.message(lambda m: m.text == "⚙️ Настройки")
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    assert message.from_user is not None
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(cast(int, message.from_user.id))
    locale = user.locale if user else "ru"
    await message.answer(
        "⚙️ <b>Настройки</b>",
        reply_markup=settings_root_keyboard(locale),
    )


@router.callback_query(F.data == "settings:close")
async def on_close(cq: CallbackQuery) -> None:
    assert cq.message is not None
    await cq.message.delete()
    await cq.answer()


@router.callback_query(F.data == "settings:locale")
async def on_open_locale(cq: CallbackQuery, session: AsyncSession) -> None:
    assert cq.message is not None
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(cast(int, cq.from_user.id))
    locale = user.locale if user else "ru"
    await cq.message.edit_text(
        "🌐 <b>Язык интерфейса</b>",
        reply_markup=locale_picker_keyboard(locale),
    )
    await cq.answer()


@router.callback_query(F.data.startswith("settings:locale:"))
async def on_pick_locale(cq: CallbackQuery, session: AsyncSession) -> None:
    assert cq.data is not None
    assert cq.message is not None
    code = cq.data.rsplit(":", 1)[1]
    settings = get_settings()
    if code not in settings.supported_locales:
        await cq.answer("Неподдерживаемый язык")
        return

    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(cast(int, cq.from_user.id))
    if user is None:
        await cq.answer("Пользователь не найден")
        return

    user.locale = code
    set_locale(code)
    await cq.answer("✓")
    await cq.message.edit_text(
        f"🌐 <b>Язык: {LOCALE_LABELS[code]}</b>",
        reply_markup=settings_root_keyboard(code),
    )


@router.callback_query(F.data == "settings:back")
async def on_back(cq: CallbackQuery, session: AsyncSession) -> None:
    assert cq.message is not None
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(cast(int, cq.from_user.id))
    locale = user.locale if user else "ru"
    await cq.message.edit_text(
        "⚙️ <b>Настройки</b>",
        reply_markup=settings_root_keyboard(locale),
    )
    await cq.answer()
