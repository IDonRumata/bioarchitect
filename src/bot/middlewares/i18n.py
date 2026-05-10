"""Middleware: установка локали из БД-профиля или ``user.language_code``.

Локаль попадает в ``data["locale"]`` и в context_var в ``src.core.i18n``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.i18n import set_locale
from src.domains.users.repository import UserRepository


class I18nMiddleware(BaseMiddleware):
    """Определяет локаль до запуска хендлера."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        settings = get_settings()
        tg_user: TgUser | None = data.get("event_from_user")
        session: AsyncSession | None = data.get("session")

        locale = settings.default_locale

        if session is not None and tg_user is not None:
            repo = UserRepository(session)
            user = await repo.get_by_telegram_id(tg_user.id)
            if user is not None and user.locale in settings.supported_locales:
                locale = user.locale
            elif tg_user.language_code:
                short = tg_user.language_code.split("-", 1)[0]
                if short in settings.supported_locales:
                    locale = short

        set_locale(locale)
        data["locale"] = locale
        return await handler(event, data)
