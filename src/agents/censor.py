"""Censor Agent — финальный фильтр AI-ответов.

КРИТИЧНОЕ требование ТЗ: нельзя отключить ни на одном тарифе.

Архитектура:
    1. Системный blacklist (программный, не через LLM):
       T1D, беременность, н/л, онкология, психиатрия, РПП, стероиды,
       лекарственные взаимодействия, диагностика, дозировки.
       Проверяется regex/keyword-классификатором ДО LLM-вызова.
    2. LLM-фильтр на Haiku 4.5: оценивает оставшиеся ответы на soft-нарушения,
       решает kept/blocked/rewrite.
    3. Автоматическое добавление дисклеймера к каждому health-ответу.

Eval suite: tests/agents/censor/*.yaml — 80+ кейсов.
CI gate: critical accuracy ≥ 98%, kept violations = 0.

Реализация — спринт 7-8.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CensorDecision(StrEnum):
    """Решение Censor Agent по конкретному ответу."""

    KEPT = "kept"          # ответ безопасен, отправлять как есть
    REWRITTEN = "rewritten"  # ответ переписан, отправить новую версию
    BLOCKED = "blocked"    # ответ заблокирован, отправить fallback


@dataclass(frozen=True)
class CensorResult:
    """Результат прогона ответа через Censor."""

    decision: CensorDecision
    final_text: str
    blocked_categories: tuple[str, ...]
    requires_disclaimer: bool


class CensorAgent:
    """Финальный фильтр AI-ответов.

    Использование::

        result = await censor.review(
            agent_name="rag",
            user_input="что такое ТТГ",
            ai_response="...",
            user_locale="ru",
        )
        await bot.send(result.final_text)
    """

    # Системный blacklist — список запрещённых категорий из ТЗ.
    BLACKLIST_CATEGORIES = (
        "type_1_diabetes",
        "insulin_management",
        "pregnancy",
        "minors",
        "oncology",
        "psychiatric_drugs",
        "eating_disorders",
        "anabolic_steroids",
        "drug_interactions",
        "post_operative_nutrition",
        "diagnosis",
        "dosage_prescription",
    )

    # TODO(sprint-7): реализовать review() с Haiku 4.5 + Prompt Caching системного промпта
    # TODO(sprint-7): загрузить eval suite из tests/agents/censor/*.yaml
    # TODO(sprint-7): метрика kept_violations (must = 0)
