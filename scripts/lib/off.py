"""Open Food Facts — клиент для поиска брендовых продуктов.

API: https://world.openfoodfacts.org/api/v2/search
Лицензия: ODbL (требует attribution в UI — добавим в /about в спринте 6).
Без ключа, public.

Стратегия: запрашиваем популярные продукты по странам присутствия ЦА
(PL, DE, GB) с порогом ``unique_scans_n``, чтобы получить реально
встречающиеся товары, а не нишевые. Каждый продукт может иметь
многоязычные названия (``product_name_en/ru/pl/de``) — заводим алиасы
сразу на всё доступное.

OFF rate limit: 100 req/min без ключа. Постранично с задержкой.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.core.logging import get_logger

log = get_logger(__name__)

OFF_BASE_URL = "https://world.openfoodfacts.org"

# Поля, которые просим — экономит трафик.
_FIELDS = ",".join(
    [
        "code",
        "product_name",
        "product_name_en",
        "product_name_ru",
        "product_name_pl",
        "product_name_de",
        "brands",
        "nutriments",
        "serving_quantity",
        "unique_scans_n",
        "countries_tags",
    ]
)

# Какие ключи смотреть в nutriments (на 100 г). Все значения в OFF — float.
_NUTRIMENT_KEYS = {
    "kcal_100g": "energy-kcal_100g",
    "protein_100g": "proteins_100g",
    "fat_100g": "fat_100g",
    "carbs_100g": "carbohydrates_100g",
    "fiber_100g": "fiber_100g",
}

_LOCALE_FIELD_MAP = {
    "en": "product_name_en",
    "ru": "product_name_ru",
    "pl": "product_name_pl",
    "de": "product_name_de",
}


@dataclass(frozen=True)
class OFFProduct:
    """Нормализованная запись из Open Food Facts."""

    code: str
    name: str  # каноническое (en если есть, иначе любое)
    brand: str | None
    kcal_100g: float
    protein_100g: float
    fat_100g: float
    carbs_100g: float
    fiber_100g: float | None
    serving_g: float | None
    aliases: dict[str, list[str]] = field(default_factory=dict)


class OFFClient:
    """Async-клиент Open Food Facts."""

    def __init__(self, timeout: float = 30.0, request_delay: float = 0.7) -> None:
        # request_delay — задержка между страницами (анти-rate-limit).
        self._client = httpx.AsyncClient(
            base_url=OFF_BASE_URL,
            timeout=timeout,
            headers={"User-Agent": "bioarchitect-seeder/0.1 (contact: support@bioarchitect.app)"},
        )
        self._delay = request_delay

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> OFFClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def fetch_popular(
        self,
        *,
        country_tag: str = "germany",
        min_scans: int = 50,
        page_size: int = 100,
        max_pages: int = 5,
    ) -> list[OFFProduct]:
        """Вытащить топ-популярные продукты по стране.

        Args:
            country_tag: tag в формате OFF (lowercase, английский: "germany",
                "poland", "united-kingdom"). RU не покрывается OFF широко.
            min_scans: фильтр по ``unique_scans_n`` — отсекает мусор.
            page_size: 1..100.
            max_pages: ограничение, чтобы не утопиться в каталоге.
        """
        out: list[OFFProduct] = []
        page = 1
        while page <= max_pages:
            params: dict[str, Any] = {
                "countries_tags_en": country_tag,
                "fields": _FIELDS,
                "page_size": page_size,
                "page": page,
                "sort_by": "unique_scans_n",
            }
            log.info("off.fetch_page", country=country_tag, page=page)
            response = await self._client.get("/api/v2/search", params=params)
            response.raise_for_status()
            payload = response.json()

            products = payload.get("products") or []
            if not products:
                break

            for raw in products:
                scans = raw.get("unique_scans_n") or 0
                if isinstance(scans, (int, float)) and scans < min_scans:
                    continue
                p = _parse_product(raw)
                if p is not None:
                    out.append(p)

            if len(products) < page_size:
                break
            page += 1
            await asyncio.sleep(self._delay)

        log.info("off.fetch_done", country=country_tag, count=len(out))
        return out


def _parse_product(raw: dict[str, Any]) -> OFFProduct | None:
    """Преобразовать сырой OFF-продукт в ``OFFProduct``.

    Отбрасываем записи без kcal/protein или с явно битыми значениями.
    """
    code = raw.get("code")
    if not isinstance(code, str) or not code:
        return None

    nutriments = raw.get("nutriments") or {}
    kcal = _safe_float(nutriments.get(_NUTRIMENT_KEYS["kcal_100g"]))
    protein = _safe_float(nutriments.get(_NUTRIMENT_KEYS["protein_100g"]))
    if kcal is None or protein is None:
        return None
    if not (0 <= kcal <= 1000):
        return None

    fat = _safe_float(nutriments.get(_NUTRIMENT_KEYS["fat_100g"])) or 0.0
    carbs = _safe_float(nutriments.get(_NUTRIMENT_KEYS["carbs_100g"])) or 0.0
    fiber = _safe_float(nutriments.get(_NUTRIMENT_KEYS["fiber_100g"]))
    if any(v < 0 for v in (protein, fat, carbs)):
        return None

    aliases: dict[str, list[str]] = {}
    canonical: str | None = None
    for locale, field_name in _LOCALE_FIELD_MAP.items():
        value = raw.get(field_name)
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                aliases[locale] = [cleaned[:256]]
                if canonical is None and locale == "en":
                    canonical = cleaned

    fallback = (raw.get("product_name") or "").strip()
    if canonical is None:
        canonical = fallback or next(iter(aliases.values()), [""])[0]
    if not canonical:
        return None

    brand_raw = raw.get("brands")
    brand: str | None = None
    if isinstance(brand_raw, str) and brand_raw.strip():
        # OFF возвращает "Brand1,Brand2" — берём первый.
        brand = brand_raw.split(",", 1)[0].strip()[:128]

    serving_q = _safe_float(raw.get("serving_quantity"))
    if serving_q is not None and not (0 < serving_q <= 5000):
        serving_q = None

    return OFFProduct(
        code=code[:64],
        name=canonical[:256],
        brand=brand,
        kcal_100g=round(kcal, 2),
        protein_100g=round(protein, 2),
        fat_100g=round(fat, 2),
        carbs_100g=round(carbs, 2),
        fiber_100g=round(fiber, 2) if fiber is not None else None,
        serving_g=serving_q,
        aliases=aliases,
    )


def _safe_float(v: object) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None
