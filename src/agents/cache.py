"""pHash-кэш для Vision API.

Похожие фото (perceptual hash distance ≤ 5) за последние 30 дней
отдаются из кэша с вопросом пользователю "та же тарелка что вчера?".
Экономия 60-80% Vision-вызовов.

Хранилище: PostgreSQL ``photo_recognitions`` (search по hex-префиксу +
in-memory hamming distance).

Реализация — спринт 4.
"""

from __future__ import annotations
