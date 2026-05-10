"""Сидинг всех справочников. Точка входа для ``make seed``.

На текущий момент (спринт 3) поднят только food-сидер.
Остальные подключатся по мере готовности:
    - seed_chain_menus.py  — спринт 5 (заправки/фастфуд через PDF-парсер)
    - seed_lab_markers.py  — спринт 10 (lab markers + reference ranges)
    - seed_articles.py     — спринт 8 (RAG education content)
"""

from __future__ import annotations

import asyncio

from scripts.seed_food_items import main as seed_food


async def _run() -> None:
    print("[seed_all] 1/4 — food_items (manual + USDA + Open Food Facts)")
    await seed_food()
    print("[seed_all] 2/4 — chain_menus    — TODO в спринте 5")
    print("[seed_all] 3/4 — lab_markers    — TODO в спринте 10 (требует медэдвайзера)")
    print("[seed_all] 4/4 — articles (RAG) — TODO в спринте 8")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
