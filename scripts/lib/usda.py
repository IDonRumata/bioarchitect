"""USDA FoodData Central — клиент для скачивания базовых продуктов.

Источник: https://fdc.nal.usda.gov (правительственный, public domain).

Используется ``foods/list`` endpoint с фильтром по ``dataType``:
    - ``Foundation`` — базовые продукты (~340 шт.).
    - ``SR Legacy`` — Standard Reference Legacy (~7800 шт., wider coverage).

Требуется API key. Бесплатный, регистрация:
https://fdc.nal.usda.gov/api-key-signup.html

При отсутствии ключа в Settings — сидер пропускает USDA-источник
(сообщение в логе) и продолжает с manual + Open Food Facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from src.core.logging import get_logger

log = get_logger(__name__)

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Маппинг nutrient_id из USDA → наши поля (на 100 г).
# Полный список: https://fdc.nal.usda.gov/portal-data/external/dataDictionary
_NUTRIENT_IDS: dict[str, int] = {
    "kcal_100g": 1008,        # Energy
    "protein_100g": 1003,     # Protein
    "fat_100g": 1004,         # Total lipid (fat)
    "carbs_100g": 1005,       # Carbohydrate, by difference
    "fiber_100g": 1079,       # Fiber, total dietary
}


@dataclass(frozen=True)
class USDAFood:
    """Нормализованная USDA-запись для сидера."""

    fdc_id: int
    description: str
    kcal_100g: float
    protein_100g: float
    fat_100g: float
    carbs_100g: float
    fiber_100g: float | None


class USDAClient:
    """Тонкий async-клиент над FDC API.

    Используется ТОЛЬКО в сидерах. В рантайме проекта ничего не вызывает FDC.
    """

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        if not api_key:
            raise ValueError("USDA API key is empty — set USDA_FDC_API_KEY in .env")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=USDA_BASE_URL,
            timeout=timeout,
            headers={"User-Agent": "bioarchitect-seeder/0.1"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> USDAClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def fetch_foods(
        self,
        *,
        data_type: Literal["Foundation", "SR Legacy"] = "Foundation",
        page_size: int = 200,
        max_pages: int | None = None,
    ) -> list[USDAFood]:
        """Скачать продукты постранично.

        Args:
            data_type: ``Foundation`` (~340) или ``SR Legacy`` (~7800).
            page_size: 1..200, FDC лимит — 200.
            max_pages: ограничить число страниц (для отладки/тестов).

        Returns:
            Список нормализованных продуктов.
        """
        out: list[USDAFood] = []
        page = 1
        while True:
            params: dict[str, Any] = {
                "api_key": self._api_key,
                "dataType": data_type,
                "pageSize": page_size,
                "pageNumber": page,
            }
            log.info("usda.fetch_page", data_type=data_type, page=page)
            response = await self._client.get("/foods/list", params=params)
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, list):
                raise RuntimeError(f"USDA: unexpected response shape on page {page}")

            if not payload:
                break

            for raw in payload:
                food = _parse_food(raw)
                if food is not None:
                    out.append(food)

            if len(payload) < page_size:
                break
            page += 1
            if max_pages is not None and page > max_pages:
                break

        log.info("usda.fetch_done", data_type=data_type, count=len(out))
        return out


def _parse_food(raw: dict[str, Any]) -> USDAFood | None:
    """Преобразовать сырой ответ FDC в ``USDAFood``.

    Возвращает None, если отсутствуют ключевые нутриенты (kcal или protein):
    такие записи в каталоге бесполезны.
    """
    fdc_id = raw.get("fdcId")
    description = (raw.get("description") or "").strip()
    if not isinstance(fdc_id, int) or not description:
        return None

    nutrients_by_id: dict[int, float] = {}
    for n in raw.get("foodNutrients", []) or []:
        nid = n.get("number")
        # number — строка (e.g. "208"), id — int — используем number.
        if nid is None:
            continue
        try:
            nid_int = int(nid)
        except (TypeError, ValueError):
            continue
        amount = n.get("amount")
        if isinstance(amount, (int, float)):
            nutrients_by_id[nid_int] = float(amount)

    kcal = nutrients_by_id.get(_NUTRIENT_IDS["kcal_100g"])
    protein = nutrients_by_id.get(_NUTRIENT_IDS["protein_100g"])
    if kcal is None or protein is None:
        return None

    fat = nutrients_by_id.get(_NUTRIENT_IDS["fat_100g"], 0.0)
    carbs = nutrients_by_id.get(_NUTRIENT_IDS["carbs_100g"], 0.0)
    fiber = nutrients_by_id.get(_NUTRIENT_IDS["fiber_100g"])

    # USDA иногда отдаёт kcal > 1000 для пряностей/специй (на 100 г сухого
    # вещества) — отбрасываем, чтобы не нарушить ck_food_items_kcal_range.
    if not (0 <= kcal <= 1000):
        return None
    if any(v < 0 for v in (protein, fat, carbs)):
        return None

    return USDAFood(
        fdc_id=fdc_id,
        description=description[:256],
        kcal_100g=round(kcal, 2),
        protein_100g=round(protein, 2),
        fat_100g=round(fat, 2),
        carbs_100g=round(carbs, 2),
        fiber_100g=round(fiber, 2) if fiber is not None else None,
    )
