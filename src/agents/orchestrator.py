"""Orchestrator — классификация пользовательского ввода.

В спринте 3 — детерминированный классификатор для текстовых сообщений
(распознавание «есть число + еда» = nutrition.text_input). Этого
достаточно для MVP: 95% реальных запросов на питание содержат явно
указанный вес или единицу.

Расширения в следующих спринтах:
    - Спринт 4: photo → vision_phase1 / ocr_lab по эвристике caption.
    - Спринт 6: вопросы пользователя → rag / coach.
    - Спринт 7: LLM-fallback для двусмысленностей (Haiku, дешёвый).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class IntentType(StrEnum):
    """Куда маршрутизировать сообщение."""

    NUTRITION_TEXT = "nutrition_text"
    PHOTO_FOOD = "photo_food"           # спринт 4
    PHOTO_LAB = "photo_lab"             # спринт 4
    QUESTION = "question"               # спринт 6 (RAG)
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Intent:
    """Результат классификации."""

    type: IntentType
    confidence: float  # 0.0..1.0


# Числа + единицы на 4 языках. \d+(?:[.,]\d+)? — целое или десятичное.
# (?i) делает кириллические/латинские буквы регистронезависимыми.
_NUTRITION_PATTERN = re.compile(
    r"(?i)\b\d+(?:[.,]\d+)?\s*(?:"
    r"г|гр|грамм|"             # ru
    r"кг|"                     # ru
    r"g|gr|gram|gramm|"        # en/de
    r"kg|kilogram|"            # en/de
    r"шт|штук[аи]?|"           # ru
    r"pcs|pieces?|stück"       # en/de
    r")\b"
)
# Эвристика 2: «число в начале строки + слово» («2 яйца», «3 apples»).
# Срабатывает только в начале — иначе слишком много ложных матчей.
_NUTRITION_LEADING_NUMBER = re.compile(r"^\s*\d+(?:[.,]\d+)?\s+\S+")
# Эвристика 3: глагол «съел/ate/...» — тогда дальше скорее всего еда.
_NUTRITION_FALLBACK = re.compile(
    r"(?i)(?:съел|поел|пообедал|позавтракал|поужинал|"
    r"ate|eaten|breakfast|lunch|dinner|"
    r"jadłem|gegessen|frühstück|mittagessen|abendessen)"
)
# Простой признак вопроса.
_QUESTION_PATTERN = re.compile(r"(?i)(?:как|что|почему|why|what|how|wieso|wie|warum|jak|co|dlaczego)\b.*\?")


class Orchestrator:
    """Детерминированный роутер пользовательского ввода.

    Для текстов:
        - Совпало с «число + единица еды» → NUTRITION_TEXT (confidence 0.95).
        - Совпало с глаголом «съел/ate/...» → NUTRITION_TEXT (0.7).
        - Заканчивается на ? и начинается с вопросительного слова → QUESTION.
        - Всё остальное → UNKNOWN.
    """

    def classify_text(self, text: str) -> Intent:
        cleaned = text.strip()
        if not cleaned:
            return Intent(IntentType.UNKNOWN, 0.0)

        if _NUTRITION_PATTERN.search(cleaned):
            return Intent(IntentType.NUTRITION_TEXT, 0.95)

        # Вопрос побеждает leading-number, если строка явно вопросительная.
        if _QUESTION_PATTERN.search(cleaned):
            return Intent(IntentType.QUESTION, 0.6)

        if _NUTRITION_LEADING_NUMBER.match(cleaned):
            return Intent(IntentType.NUTRITION_TEXT, 0.92)

        if _NUTRITION_FALLBACK.search(cleaned):
            return Intent(IntentType.NUTRITION_TEXT, 0.7)

        return Intent(IntentType.UNKNOWN, 0.0)
