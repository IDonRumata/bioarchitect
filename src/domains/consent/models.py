"""Модели домена consent.

Таблицы:
    - consent_records    (append-only лог согласий, GDPR Art. 9)
    - data_export_requests
    - data_deletion_requests

Реализация — спринт 2.
"""

from __future__ import annotations
