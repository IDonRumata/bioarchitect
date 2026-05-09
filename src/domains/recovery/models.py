"""Модели домена recovery.

Таблицы:
    - daily_checkins              (immutable: вес, давление, сон, энергия)
    - recovery_index_history      (RI 0-100, components_json)

Реализация — спринт 5.
"""

from __future__ import annotations
