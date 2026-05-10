"""Enum-типы домена consent."""

from __future__ import annotations

from enum import StrEnum


class ConsentType(StrEnum):
    """Тип согласия.

    Каждый тип — отдельная legal basis под GDPR. Хранится append-only.
    """

    # GDPR Art. 6(1)(b) — performance of contract (использование сервиса)
    TERMS_OF_SERVICE = "terms_of_service"

    # GDPR Art. 9(2)(a) — explicit consent for processing health data
    HEALTH_DATA_PROCESSING = "health_data_processing"

    # GDPR Art. 6(1)(f) — legitimate interest, but with opt-in for analytics
    ANALYTICS = "analytics"

    # Маркетинговые рассылки (Free → Pro upsell)
    MARKETING = "marketing"

    # Обработка фото бланков анализов (отдельное согласие — особо чувствительные данные)
    LAB_REPORT_STORAGE = "lab_report_storage"
