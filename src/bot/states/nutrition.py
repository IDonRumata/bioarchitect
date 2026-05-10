"""FSM-состояния для логирования еды через текстовый ввод.

Сценарий:
    1. Пользователь пишет «куриная грудка 200г, рис 150г».
    2. Orchestrator классифицирует → nutrition.text_input.
    3. NutritionParser (Haiku) → ParsedFoodEntry-список.
    4. Для каждой entry — fuzzy search в food_aliases.
    5. Если 1 кандидат с similarity ≥ 0.85 → авто-выбор + лог.
    6. Иначе → бот показывает inline-кнопки с топ-3.
       state = ``choosing_match`` хранит «очередь» entries и текущий индекс.
    7. После обработки очереди — bot шлёт сводку и сбрасывает state.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class NutritionStates(StatesGroup):
    """States логирования еды."""

    # Пользователь видит кнопки выбора кандидата для одной из распознанных entries.
    choosing_match = State()
