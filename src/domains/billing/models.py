"""Модели домена billing.

Таблицы:
    - subscriptions    (plan_id, status, provider, period_start/end)
    - payments         (платёжный лог, raw_webhook для аудита)
    - llm_calls        (аудит LLM, partitioned по месяцам, для биллинга)

Провайдеры: Stripe, Telegram Stars, ЮKassa.

Реализация — спринт 7.
"""

from __future__ import annotations
