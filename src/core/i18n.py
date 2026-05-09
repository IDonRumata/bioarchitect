"""i18n: загрузка переводов из ``locale/<lang>/LC_MESSAGES/messages.mo``.

Поддерживаемые языки: ru, en, pl, de. Локаль пользователя хранится в
``user_profiles.locale`` и подставляется в context_var на каждый запрос.
"""

from __future__ import annotations

import gettext
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

from src.core.config import get_settings

LOCALE_DIR = Path(__file__).resolve().parents[2] / "locale"
DOMAIN = "messages"

_current_locale: ContextVar[str] = ContextVar("current_locale", default="ru")


@lru_cache(maxsize=8)
def _translation(lang: str) -> gettext.NullTranslations:
    return gettext.translation(
        domain=DOMAIN,
        localedir=str(LOCALE_DIR),
        languages=[lang],
        fallback=True,
    )


def set_locale(lang: str) -> None:
    """Установить локаль для текущего контекста (asyncio task)."""
    settings = get_settings()
    if lang not in settings.supported_locales:
        lang = settings.default_locale
    _current_locale.set(lang)


def get_locale() -> str:
    return _current_locale.get()


def gettext_(message: str) -> str:
    """Перевести сообщение в текущую локаль."""
    return _translation(get_locale()).gettext(message)


def ngettext_(singular: str, plural: str, n: int) -> str:
    return _translation(get_locale()).ngettext(singular, plural, n)


# Псевдоним для удобства: from src.core.i18n import _
_ = gettext_
