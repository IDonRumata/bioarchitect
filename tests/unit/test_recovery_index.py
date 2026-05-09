"""Тесты Recovery Index — детерминированный алгоритм."""

from __future__ import annotations

import pytest

from src.domains.recovery.index import compute_recovery_index


@pytest.mark.unit
def test_perfect_day_score_close_to_100() -> None:
    """8ч сна, давление 120, энергия 10, стрик 7 — около максимума."""
    r = compute_recovery_index(
        sleep_hours=8.0,
        bp_systolic=120,
        energy_level=10,
        streak_days=7,
    )
    assert r.total == 100


@pytest.mark.unit
def test_no_data_yields_zero() -> None:
    r = compute_recovery_index(
        sleep_hours=None,
        bp_systolic=None,
        energy_level=None,
        streak_days=0,
    )
    assert r.total == 0


@pytest.mark.unit
def test_extreme_blood_pressure_does_not_go_negative() -> None:
    """Защита от отрицательного вклада: давление 200 → bp_component = 0."""
    r = compute_recovery_index(
        sleep_hours=8.0,
        bp_systolic=200,
        energy_level=10,
        streak_days=7,
    )
    # sleep 35 + bp 0 + energy 25 + streak 15 = 75
    assert r.blood_pressure == 0.0
    assert r.total == 75


@pytest.mark.unit
def test_streak_capped_at_seven_days() -> None:
    """Стрик более 7 дней не даёт дополнительных баллов сверх 15."""
    r1 = compute_recovery_index(
        sleep_hours=8.0,
        bp_systolic=120,
        energy_level=10,
        streak_days=7,
    )
    r2 = compute_recovery_index(
        sleep_hours=8.0,
        bp_systolic=120,
        energy_level=10,
        streak_days=30,
    )
    assert r1.streak_bonus == r2.streak_bonus == 15.0
    assert r1.total == r2.total


@pytest.mark.unit
def test_oversleeping_does_not_overshoot() -> None:
    """12ч сна не даёт более 35 баллов (clamp работает)."""
    r = compute_recovery_index(
        sleep_hours=12.0,
        bp_systolic=120,
        energy_level=10,
        streak_days=7,
    )
    assert r.sleep == 35.0
    assert r.total == 100
