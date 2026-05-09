"""Recovery Index — детерминированный алгоритм 0-100.

НЕ использует LLM. Формула из ТЗ с защитой от экстремальных значений
(clamp каждой компоненты в [0, max], чтобы давление 200/100 не давало
отрицательный вклад).

Состав:
    - sleep_component   (35 баллов max): sleep_hours / 8 * 35, clamp [0, 35]
    - bp_component      (25 баллов max): отклонение от 120 систолического
    - energy_component  (25 баллов max): energy_level / 10 * 25
    - streak_bonus      (15 баллов max): стрик ежедневных check-in за 7 дней
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryComponents:
    """Декомпозиция Recovery Index. Хранится в БД как JSON."""

    sleep: float
    blood_pressure: float
    energy: float
    streak_bonus: float

    @property
    def total(self) -> int:
        """Финальный Recovery Index, округлённый до int."""
        return round(self.sleep + self.blood_pressure + self.energy + self.streak_bonus)


def compute_recovery_index(
    *,
    sleep_hours: float | None,
    bp_systolic: int | None,
    energy_level: int | None,
    streak_days: int = 0,
) -> RecoveryComponents:
    """Вычислить Recovery Index из данных daily check-in.

    Args:
        sleep_hours: Часы сна (0-24). None — компонента 0.
        bp_systolic: Систолическое давление в мм рт. ст. None — компонента 0.
        energy_level: Уровень энергии 1-10. None — компонента 0.
        streak_days: Длина стрика ежедневных check-in (макс. 7 учитывается).

    Returns:
        Декомпозированный Recovery Index.

    Note:
        Все компоненты clamp в [0, max], чтобы экстремальные значения
        не давали отрицательный итог. Это отличается от наивной формулы
        в ТЗ и фиксируется в ADR-0004.
    """
    sleep = (sleep_hours or 0.0) / 8.0 * 35.0
    sleep = max(0.0, min(35.0, sleep))

    if bp_systolic is None:
        bp = 0.0
    else:
        # Отклонение от 120: каждые 8 единиц = -1 балл из 8 максимума.
        deviation = abs(bp_systolic - 120) / 8.0
        bp_score = 8.0 - deviation
        bp = max(0.0, bp_score) / 8.0 * 25.0
    bp = max(0.0, min(25.0, bp))

    energy = (energy_level or 0) / 10.0 * 25.0
    energy = max(0.0, min(25.0, energy))

    streak = min(streak_days, 7) / 7.0 * 15.0
    streak = max(0.0, min(15.0, streak))

    return RecoveryComponents(
        sleep=sleep,
        blood_pressure=bp,
        energy=energy,
        streak_bonus=streak,
    )
