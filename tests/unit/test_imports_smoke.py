"""Smoke-тест: каждый модуль проекта импортируется без ошибок.

Это самый дешёвый способ поймать опечатки в импортах, опечатки в Pydantic
схемах и сломанные ссылки между модулями. Запускается как часть unit-сюиты.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import src


@pytest.mark.unit
def test_all_src_modules_import() -> None:
    """Импортируем все модули в ``src/`` рекурсивно."""
    failures: list[tuple[str, str]] = []
    for module_info in _iter_modules(src):
        try:
            importlib.import_module(module_info)
        except Exception as exc:  # noqa: BLE001 — собираем все, не только импорт-ошибки
            failures.append((module_info, f"{type(exc).__name__}: {exc}"))
    assert not failures, "Failed imports:\n" + "\n".join(
        f"  - {m}: {err}" for m, err in failures
    )


def _iter_modules(package: object) -> list[str]:
    """Рекурсивный обход пакета, возвращает полные dotted-имена модулей."""
    modules: list[str] = []
    package_path = package.__path__  # type: ignore[attr-defined]
    package_name = package.__name__  # type: ignore[attr-defined]
    for _, name, is_pkg in pkgutil.iter_modules(package_path):
        full = f"{package_name}.{name}"
        modules.append(full)
        if is_pkg:
            sub = importlib.import_module(full)
            modules.extend(_iter_modules(sub))
    return modules
