"""FSM-состояния для потока распознавания еды по фото (Vision Phase 1).

Сценарий:
    1. Пользователь отправляет фото.
    2. VisionParser → Phase1Result (список RecognizedItem).
    3. Бот показывает первый элемент с кнопками «✅ Ок / ✏️ Изменить граммы / ❌ Пропустить».
       state = ``confirming_item`` хранит очередь и текущий индекс.
    4. На «✏️ Изменить граммы» → state = ``entering_grams``, ждём ввода числа.
    5. После обработки всей очереди → сводка + сброс state.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class VisionStates(StatesGroup):
    """States потока Vision Phase 1."""

    # Пользователь подтверждает / пропускает / редактирует распознанный элемент.
    confirming_item = State()
    # Пользователь вводит граммы вручную (после нажатия «Изменить граммы»).
    entering_grams = State()
