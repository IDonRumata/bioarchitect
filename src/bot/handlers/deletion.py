"""``/delete`` — soft-delete с 30-дневным grace period.

Поток:
    1. Пользователь жмёт `/delete` или кнопку "Удалить аккаунт" в /settings.
    2. Бот показывает подтверждение (кнопки "удалить" / "отмена").
    3. При подтверждении: ``UserService.request_deletion`` ставит status =
       PENDING_DELETION + deletion_requested_at = now().
    4. ARQ-воркер ``data_deletion_processor`` (см. src/workers/) ежедневно
       проверяет таблицу users и hard-delete'ит тех, у кого
       deletion_requested_at + 30 дней < now().
    5. В течение grace period пользователь может откатить через /start
       (там показывается deletion_undo_keyboard) или кнопка undo здесь.
"""

from __future__ import annotations

from typing import cast

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.main_menu import main_menu_keyboard, remove_main_menu
from src.bot.keyboards.settings import delete_confirmation_keyboard
from src.core.logging import get_logger
from src.domains.users.enums import UserStatus
from src.domains.users.repository import UserRepository
from src.domains.users.service import UserService

log = get_logger(__name__)
router = Router(name="deletion")


@router.message(Command("delete"))
@router.callback_query(F.data == "settings:delete")
async def request_deletion(
    event: Message | CallbackQuery,
) -> None:
    text = (
        "🗑 <b>Удаление аккаунта (GDPR)</b>\n\n"
        "Если ты подтвердишь:\n"
        "• Все твои данные (профиль, питание, анализы, чек-ины) "
        "помечаются на удаление\n"
        "• 30 дней — на отмену, если передумаешь\n"
        "• По истечении grace period — <b>безвозвратное удаление</b>\n\n"
        "Это твоё право по GDPR Art. 17. Уверен?"
    )
    if isinstance(event, Message):
        await event.answer(
            text,
            reply_markup=delete_confirmation_keyboard(),
        )
    else:
        assert event.message is not None
        await event.message.edit_text(text, reply_markup=delete_confirmation_keyboard())
        await event.answer()


@router.callback_query(F.data == "delete:confirm")
async def on_confirm(cq: CallbackQuery, session: AsyncSession) -> None:
    assert cq.message is not None
    user_service = UserService(session)
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(cast(int, cq.from_user.id))
    if user is None:
        await cq.answer("Аккаунт не найден")
        return

    await user_service.request_deletion(user)
    log.info("user.deletion_requested", user_id=str(user.id))
    await cq.message.edit_text(
        "🕒 <b>Удаление запланировано.</b>\n\n"
        "Твои данные будут безвозвратно удалены через 30 дней. "
        "Если передумаешь — нажми /start и выбери «Отменить удаление»."
    )
    await cq.answer("Запрос принят")


@router.callback_query(F.data == "delete:cancel")
async def on_cancel(cq: CallbackQuery) -> None:
    assert cq.message is not None
    await cq.message.edit_text("Хорошо, ничего не удаляю.")
    await cq.answer()


@router.callback_query(F.data == "delete:undo")
async def on_undo_deletion(cq: CallbackQuery, session: AsyncSession) -> None:
    assert cq.message is not None
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(cast(int, cq.from_user.id))
    if user is None or user.status != UserStatus.PENDING_DELETION:
        await cq.answer("Нечего отменять")
        return

    user.status = UserStatus.ACTIVE
    user.deletion_requested_at = None
    log.info("user.deletion_undone", user_id=str(user.id))
    await cq.message.edit_text(
        "✅ <b>Удаление отменено.</b> Твои данные сохранены.",
    )
    # Возвращаем главное меню
    await cq.message.answer("С возвращением!", reply_markup=main_menu_keyboard())
    await cq.answer("Удаление отменено")


@router.message(Command("restore"))
async def cmd_restore(message: Message, session: AsyncSession) -> None:
    """Альтернативная команда отмены удаления."""
    assert message.from_user is not None
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(cast(int, message.from_user.id))
    if user is None or user.status != UserStatus.PENDING_DELETION:
        await message.answer("Нечего восстанавливать.", reply_markup=remove_main_menu())
        return
    user.status = UserStatus.ACTIVE
    user.deletion_requested_at = None
    await message.answer(
        "✅ Удаление отменено. С возвращением!",
        reply_markup=main_menu_keyboard(),
    )
