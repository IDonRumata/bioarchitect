"""Модели домена lab_results.

Таблицы:
    - lab_markers              (каталог: ТТГ, св.Т4, тестостерон, ...)
    - lab_reference_ranges     (референсы по странам, verified_by медэдвайзером)
    - lab_reports              (бланки анализов, ссылка на зашифрованное B2-фото)
    - lab_marker_results       (immutable, position детерминированно вычислен)

ВАЖНО: интерпретация значений запрещена. Только in_range / below / above.

Реализация — спринты 13-14.
"""

from __future__ import annotations
