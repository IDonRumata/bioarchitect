"""Хендлер ``/start`` — точка входа в бота.

В спринте 1 — заглушка с приветствием.
В спринте 2 — полный онбординг FSM (5 шагов + GDPR-согласие).
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Заглушка приветствия. Полная FSM — в спринте 2."""
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Это BioArchitect — твой AI-помощник по питанию и самочувствию для рейсов "
        "и вахт.\n\n"
        "🚧 Бот в активной разработке. Скоро здесь появится онбординг."
    )
