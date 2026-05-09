"""OCR Lab Agent — извлечение лабораторных маркеров из фото бланка.

Модель: Claude Sonnet 4.6 Vision.
Output: tool_use со строгой схемой (маркер, значение, единицы, референс
лаборатории если указан).

При confidence < 0.7 для любого маркера — запрос ручного ввода.

Детерминированный код вычисляет position (below/in_range/above), Censor —
не запускается на pure data.

Реализация — спринт 13.
"""

from __future__ import annotations
