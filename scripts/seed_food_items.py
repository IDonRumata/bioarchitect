"""Сидинг food_items + food_aliases.

Использование::

    uv run python -m scripts.seed_food_items                # все источники
    uv run python -m scripts.seed_food_items --only manual  # только базовый
    uv run python -m scripts.seed_food_items --skip usda    # без USDA
    uv run python -m scripts.seed_food_items --usda-limit 2 # 2 страницы USDA
    uv run python -m scripts.seed_food_items --off-countries germany,poland

USDA требует API key (``USDA_FDC_API_KEY`` в .env). При отсутствии —
USDA-источник пропускается с предупреждением.

Идемпотентен: повторный запуск не плодит дубликатов.
"""

from __future__ import annotations

import argparse
import asyncio

from src.core.config import get_settings
from src.core.db.session import get_sessionmaker
from src.core.logging import get_logger
from src.domains.nutrition.enums import FoodSource
from scripts.lib.manual_foods import MANUAL_FOODS
from scripts.lib.off import OFFClient
from scripts.lib.seeder import SeedRecord, SeedStats, upsert_records
from scripts.lib.usda import USDAClient

log = get_logger(__name__)

_DEFAULT_OFF_COUNTRIES = ("germany", "poland", "united-kingdom")


def _records_from_manual() -> list[SeedRecord]:
    return [
        SeedRecord(
            source=FoodSource.MANUAL,
            external_id=f"MANUAL-{f.slug}",
            name=f.name_en,
            kcal_100g=f.kcal_100g,
            protein_100g=f.protein_100g,
            fat_100g=f.fat_100g,
            carbs_100g=f.carbs_100g,
            fiber_100g=f.fiber_100g,
            serving_g=f.serving_g,
            brand=f.brand,
            verified=True,  # вручную выверенные значения
            aliases=dict(f.aliases),
        )
        for f in MANUAL_FOODS
    ]


async def _records_from_usda(
    api_key: str,
    *,
    max_pages: int | None,
) -> list[SeedRecord]:
    async with USDAClient(api_key=api_key) as client:
        foods = await client.fetch_foods(
            data_type="Foundation",
            page_size=200,
            max_pages=max_pages,
        )

    return [
        SeedRecord(
            source=FoodSource.USDA,
            external_id=str(f.fdc_id),
            name=f.description,
            kcal_100g=f.kcal_100g,
            protein_100g=f.protein_100g,
            fat_100g=f.fat_100g,
            carbs_100g=f.carbs_100g,
            fiber_100g=f.fiber_100g,
            serving_g=None,
            brand=None,
            verified=True,  # USDA — авторитетный источник
            aliases={"en": [f.description]},
        )
        for f in foods
    ]


async def _records_from_off(
    *,
    countries: tuple[str, ...],
    max_pages_per_country: int,
) -> list[SeedRecord]:
    out: list[SeedRecord] = []
    async with OFFClient() as client:
        for country in countries:
            products = await client.fetch_popular(
                country_tag=country,
                min_scans=50,
                page_size=100,
                max_pages=max_pages_per_country,
            )
            for p in products:
                aliases = dict(p.aliases)
                # Дублируем canonical в en, если en-алиас не отдан явно.
                aliases.setdefault("en", []).append(p.name)
                # Дедуп внутри списка.
                aliases = {
                    locale: list(dict.fromkeys(values))
                    for locale, values in aliases.items()
                    if values
                }
                out.append(
                    SeedRecord(
                        source=FoodSource.OFF,
                        external_id=p.code,
                        name=p.name,
                        kcal_100g=p.kcal_100g,
                        protein_100g=p.protein_100g,
                        fat_100g=p.fat_100g,
                        carbs_100g=p.carbs_100g,
                        fiber_100g=p.fiber_100g,
                        serving_g=p.serving_g,
                        brand=p.brand,
                        verified=False,
                        aliases=aliases,
                    )
                )

    # OFF может вернуть один и тот же barcode из разных стран — дедуп.
    seen: dict[str, SeedRecord] = {}
    for r in out:
        seen.setdefault(r.external_id, r)
    return list(seen.values())


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed food_items catalog")
    parser.add_argument(
        "--only",
        choices=["manual", "usda", "off"],
        help="Только один источник",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        choices=["manual", "usda", "off"],
        help="Пропустить источник (можно несколько раз)",
    )
    parser.add_argument(
        "--usda-limit",
        type=int,
        default=None,
        help="Максимум страниц USDA (200 записей/страница)",
    )
    parser.add_argument(
        "--off-countries",
        type=str,
        default=",".join(_DEFAULT_OFF_COUNTRIES),
        help="Страны OFF через запятую (germany,poland,united-kingdom)",
    )
    parser.add_argument(
        "--off-pages",
        type=int,
        default=2,
        help="Страниц на страну (100 продуктов/страница)",
    )
    args = parser.parse_args()

    enabled: set[str]
    if args.only:
        enabled = {args.only}
    else:
        enabled = {"manual", "usda", "off"} - set(args.skip)

    settings = get_settings()
    sessionmaker = get_sessionmaker()

    total_stats = SeedStats()

    async with sessionmaker() as session:
        if "manual" in enabled:
            log.info("seed.manual.start", count=len(MANUAL_FOODS))
            records = _records_from_manual()
            stats = await upsert_records(session, records)
            await session.commit()
            log.info("seed.manual.done", **stats.__dict__)
            _accumulate(total_stats, stats)

        if "usda" in enabled:
            api_key = settings.usda_fdc_api_key.get_secret_value()
            if not api_key:
                log.warning("seed.usda.skipped", reason="USDA_FDC_API_KEY not set in .env")
            else:
                log.info("seed.usda.start")
                records = await _records_from_usda(api_key, max_pages=args.usda_limit)
                stats = await upsert_records(session, records)
                await session.commit()
                log.info("seed.usda.done", **stats.__dict__)
                _accumulate(total_stats, stats)

        if "off" in enabled:
            countries = tuple(c.strip() for c in args.off_countries.split(",") if c.strip())
            log.info("seed.off.start", countries=countries)
            records = await _records_from_off(
                countries=countries,
                max_pages_per_country=args.off_pages,
            )
            stats = await upsert_records(session, records)
            await session.commit()
            log.info("seed.off.done", **stats.__dict__)
            _accumulate(total_stats, stats)

    log.info("seed.total", **total_stats.__dict__)
    print(
        f"[seed] items_created={total_stats.items_created} "
        f"items_updated={total_stats.items_updated} "
        f"aliases_created={total_stats.aliases_created} "
        f"aliases_skipped={total_stats.aliases_skipped}"
    )


def _accumulate(total: SeedStats, partial: SeedStats) -> None:
    total.items_created += partial.items_created
    total.items_updated += partial.items_updated
    total.aliases_created += partial.aliases_created
    total.aliases_skipped += partial.aliases_skipped


if __name__ == "__main__":
    asyncio.run(main())
