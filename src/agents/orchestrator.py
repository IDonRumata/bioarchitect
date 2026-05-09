"""Orchestrator — классификация пользовательского ввода и маршрутизация.

Решает, какой агент / handler должен обрабатывать сообщение:
    - text "куриная грудка 200г" → nutrition.text_input
    - photo + не подпись "анализы" → vision_phase1
    - photo + caption "анализы" / OCR-эвристика → ocr_lab
    - text вопрос → rag
    - command → bot handler

Реализация — спринт 3-4.
"""

from __future__ import annotations
