"""FSM-состояния онбординга.

Последовательность:
    GDPR-согласие (Art. 9) → страна → пол → год рождения → рост → вес →
    тип работы → lifestyle-теги → завершение.

Полный сценарий — 5 этапов из ТЗ §5.1 + явное согласие на обработку
health-данных (без него онбординг не завершается).
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """States онбординга. Порядок строгий, шаг назад — отдельной командой."""

    awaiting_gdpr_consent = State()
    awaiting_country = State()
    awaiting_sex = State()
    awaiting_birth_year = State()
    awaiting_height = State()
    awaiting_weight = State()
    awaiting_work_pattern = State()
    awaiting_lifestyle_tags = State()
