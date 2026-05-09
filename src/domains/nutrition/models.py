"""Модели домена nutrition.

Таблицы:
    - food_items           (USDA + Open Food Facts + chain menus, search_vector)
    - food_logs            (immutable, partitioned по месяцам)
    - photo_recognitions   (pHash-кэш, photo_kept=false всегда)
    - chain_brands         (Aral, McDonald's, Lidl, ...)
    - chain_menu_items     (Big Mac = 219г, верифицированные веса)
    - fasting_sessions     (IF-протоколы 14/10, 16/8, 18/6)

Реализация — спринты 3-6.
"""

from __future__ import annotations
