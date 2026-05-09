"""Модели домена analytics.

Таблицы:
    - analytics_events      (партиционированные по месяцам)
    - daily_aggregations    (DAU, MAU, conversion funnels)

PostHog self-hosted (опционально) подключается отдельно.

Реализация — спринт 8.
"""

from __future__ import annotations
