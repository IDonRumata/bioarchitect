"""``/profile`` — просмотр профиля пользователя.

В этом спринте — read-only. Редактирование (через под-FSM или re-onboarding)
будет в спринте 3 после того, как мы убедимся, что онбординг работает в полевых условиях.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.main_menu import main_menu_keyboard
from src.bot.keyboards.onboarding import LIFESTYLE_TAG_LABELS
from src.domains.users.enums import LifestyleTag, Sex, WorkPattern
from src.domains.users.repository import UserRepository

router = Router(name="profile")


# Текстовые лейблы для перечислений (RU). В спринте 6+ переходим на _()
SEX_LABEL: dict[Sex, str] = {
    Sex.MALE: "Мужской",
    Sex.FEMALE: "Женский",
    Sex.UNSPECIFIED: "Не указан",
}
WORK_LABEL: dict[WorkPattern, str] = {
    WorkPattern.LONG_HAUL: "Дальние рейсы",
    WorkPattern.SHIFT_WORK: "Вахта",
    WorkPattern.MIXED: "И то и то",
    WorkPattern.OFFICE: "Офис",
    WorkPattern.UNSPECIFIED: "Не указано",
}


@router.message(Command("profile"))
@router.message(lambda m: m.text == "👤 Профиль")
async def cmd_profile(message: Message, session: AsyncSession) -> None:
    """Показать сводку профиля."""
    assert message.from_user is not None
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(cast(int, message.from_user.id))

    if user is None or user.profile is None:
        await message.answer(
            "Профиль ещё не заполнен. Нажми /start, чтобы начать.",
            reply_markup=main_menu_keyboard(),
        )
        return

    profile = user.profile
    age = (datetime.now().year - profile.birth_year) if profile.birth_year else None

    tags_typed: list[LifestyleTag] = profile.lifestyle_tags_typed()
    tags_text = (
        ", ".join(LIFESTYLE_TAG_LABELS[t] for t in tags_typed) if tags_typed else "—"
    )

    text = (
        "👤 <b>Твой профиль</b>\n\n"
        f"🌍 Страна: <code>{user.country_iso or '—'}</code>\n"
        f"🌐 Язык: <code>{user.locale}</code>\n"
        f"🕐 Часовой пояс: <code>{user.timezone}</code>\n\n"
        f"⚥ Пол: {SEX_LABEL[profile.sex]}\n"
        f"🎂 Возраст: {age if age is not None else '—'}\n"
        f"📏 Рост: {profile.height_cm or '—'} см\n"
        f"⚖️ Вес: {profile.weight_kg or '—'} кг\n"
        f"💼 График: {WORK_LABEL[profile.work_pattern]}\n"
        f"🏷 Привычки: {tags_text}\n\n"
        "<i>Чтобы изменить — пока пройди онбординг заново через /start. "
        "Полноценное редактирование добавим в следующих обновлениях.</i>"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())
