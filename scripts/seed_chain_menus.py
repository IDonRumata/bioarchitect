"""Парсер nutritional PDF от сетей заправок и фастфуда.

Стратегия:
    1. Зарегистрированные сети — ``scripts/chain_pdf_sources.yaml``
       (URL PDF, селекторы таблиц, шаблоны).
    2. Скачиваем PDF, парсим через ``pdfplumber``.
    3. Извлекаем: название блюда, КБЖУ, вес порции.
    4. Нормализуем в ``chain_menu_items``.
    5. Версионирование: каждая запись с ``source_pdf_url`` и ``parsed_at``.

Запуск:
    python -m scripts.seed_chain_menus
    python -m scripts.seed_chain_menus --chain mcdonalds
    python -m scripts.seed_chain_menus --update-stale  # старше 90 дней

Реализация — спринт 8.
"""

from __future__ import annotations
