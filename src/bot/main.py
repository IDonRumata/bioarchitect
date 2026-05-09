"""Точка входа Telegram-бота.

Запуск:
    python -m src.bot.main

В dev — long polling. В продакшне — webhook через FastAPI (см. src/api/).
"""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.handlers import router as main_router
from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.core.safety import assert_safe_to_start

log = get_logger(__name__)


async def main() -> None:
    configure_logging()
    assert_safe_to_start()

    settings = get_settings()

    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(main_router)

    me = await bot.get_me()
    log.info("bot.started", username=me.username, env=settings.env.value)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
