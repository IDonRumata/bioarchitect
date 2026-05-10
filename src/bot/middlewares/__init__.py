"""Aiogram middlewares: DBSession, I18n, RateLimit, Subscription, Censor.

Порядок регистрации в dispatcher критичен: DB-сессия должна открыться
до I18n (которому нужно читать профиль из БД).
"""

from src.bot.middlewares.db_session import DBSessionMiddleware
from src.bot.middlewares.i18n import I18nMiddleware

__all__ = ["DBSessionMiddleware", "I18nMiddleware"]
