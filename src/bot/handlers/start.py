"""``/start`` — точка входа в бота.

- Если пользователь не существует или не завершил онбординг → запускаем FSM.
- Если онбординг завершён → показываем главное меню (TODO sprint 2: меню).
"""

from __future__ import annotations

from typing import cast

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.onboarding import begin_onboarding
from src.domains.users.service import UserService

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    assert message.from_user is not None
    user_service = UserService(session)
    user, created = await user_service.get_or_create(
        telegram_id=cast(int, message.from_user.id),
        username=message.from_user.username,
    )

    if created or user.onboarding_completed_at is None:
        await message.answer(
            "👋 <b>Привет!</b>\n\n"
            "Это <b>BioArchitect</b> — твой AI-помощник по питанию и "
            "самочувствию для рейсов и вахт. Работает на смартфоне без "
            "браслетов и подписок на железо.\n\n"
            "Сейчас зададу 5 коротких вопросов о тебе — это нужно, чтобы "
            "подобрать рекомендации под твой график."
        )
        await begin_onboarding(message, state)
        return

    await state.clear()
    await message.answer(
        "С возвращением! 👋\n\n"
        "Отправь фото еды, напиши «куриная грудка 200г», или /help — "
        "все команды."
    )
