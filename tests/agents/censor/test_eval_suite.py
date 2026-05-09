"""Censor Agent eval suite runner.

Загружает все YAML-кейсы из ``cases/``, прогоняет через ``CensorAgent``,
проверяет ожидаемые decision + blocked_categories + дисклеймер.

Реализация — спринт 7. Сейчас — placeholder, чтобы CI-команда ``make eval``
не падала на пустом каталоге.
"""

from __future__ import annotations

import pytest


@pytest.mark.censor_eval
def test_eval_suite_placeholder() -> None:
    """Заглушка до спринта 7. Удалить когда появятся реальные кейсы."""
    # TODO(sprint-7): загрузить cases/*.yaml через PyYAML
    # TODO(sprint-7): прогнать через CensorAgent.review()
    # TODO(sprint-7): assert critical_accuracy >= 0.98 and kept_violations == 0
