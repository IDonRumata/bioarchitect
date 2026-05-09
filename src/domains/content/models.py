"""Модели домена content.

Таблицы:
    - articles            (метаданные: автор, verified_by, sources, review_date)
    - article_chunks      (chunk_text, embedding vector(1024), language)

Реализация — спринт 9.
"""

from __future__ import annotations
