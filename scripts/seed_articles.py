"""Импорт образовательных статей из Notion в article_chunks.

Pipeline:
    Notion API → markdown → split (1024 token chunks) → embed → pgvector.

Реализация — спринт 9.
"""

from __future__ import annotations
