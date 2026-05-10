"""Vision Phase 1 — распознавание продуктов на фото.

Поток:
    1. Принять bytes фото из Telegram.
    2. Вычислить pHash (64-bit perceptual hash через imagehash).
    3. Проверить кэш в ``photo_recognitions``: если найдена запись
       с расстоянием Хэмминга ≤ PHASH_DISTANCE_THRESHOLD за последние
       PHASH_CACHE_DAYS дней — вернуть кэшированный результат.
    4. Иначе — вызвать ``ClaudeClient.call_vision`` (Sonnet 4.6).
    5. Сохранить результат в ``photo_recognitions`` (photo_kept = false).

Модель: claude-sonnet-4-6 Vision.
Output: ``<json>[...]</json>`` — список RecognizedItem.
"""

from __future__ import annotations

import io
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import imagehash
from PIL import Image
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.client import ClaudeClient, LLMCallResult
from src.core.logging import get_logger
from src.domains.nutrition.models import PhotoRecognition

log = get_logger(__name__)

# Расстояние Хэмминга между pHash, ниже которого считаем фото «одинаковыми».
PHASH_DISTANCE_THRESHOLD = 5
# Сколько дней смотрим в кэш.
PHASH_CACHE_DAYS = 30
# Системный промпт.
_PROMPT_PATH = Path(__file__).parent / "prompts" / "vision_phase1.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class RecognizedItem(BaseModel):
    """Один распознанный продукт на тарелке."""

    name_en: str = Field(..., min_length=1, max_length=200)
    name_ru: str = Field(..., min_length=1, max_length=200)
    grams_min: int = Field(..., ge=1, le=5000)
    grams_max: int = Field(..., ge=1, le=5000)
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertain: bool
    alternatives: list[str] = Field(default_factory=list)

    @property
    def grams_mid(self) -> int:
        return (self.grams_min + self.grams_max) // 2


class Phase1Result(BaseModel):
    """Полный результат Phase 1."""

    items: list[RecognizedItem]
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    # Бренд/сеть, если распознан (Big Mac → "McDonald's").
    chain_brand_detected: str | None = None
    from_cache: bool = False


class VisionParseError(Exception):
    """Не удалось разобрать ответ Vision API."""


def compute_phash(image_bytes: bytes) -> str:
    """64-bit pHash изображения, возвращает 16-символьный hex."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    h = imagehash.phash(img)
    return str(h)


def phash_hamming(a: str, b: str) -> int:
    """Расстояние Хэмминга между двумя hex pHash строками."""
    if len(a) != len(b):
        return 64  # разные размеры — максимальное расстояние
    ha = imagehash.hex_to_hash(a)
    hb = imagehash.hex_to_hash(b)
    return ha - hb  # imagehash перегружает __sub__ как hamming distance


def _parse_items(raw: str) -> list[RecognizedItem]:
    """Извлекает список RecognizedItem из ответа Vision API."""
    match = re.search(r"<json>(.*?)</json>", raw, re.DOTALL)
    if not match:
        raise VisionParseError(f"No <json>...</json> block in vision response: {raw!r}")
    try:
        data = json.loads(match.group(1).strip())
    except json.JSONDecodeError as exc:
        raise VisionParseError(f"Vision response JSON invalid: {exc}") from exc
    if not isinstance(data, list):
        raise VisionParseError(f"Vision response must be JSON array, got {type(data)}")

    items: list[RecognizedItem] = []
    for entry in data:
        try:
            items.append(RecognizedItem.model_validate(entry))
        except ValidationError as exc:
            log.warning("vision.skip_invalid_item", error=str(exc), entry=entry)
    return items


class VisionParser:
    """Принимает bytes фото, возвращает Phase1Result + LLMCallResult."""

    def __init__(self) -> None:
        self._client = ClaudeClient()
        self._system = _load_prompt()

    async def recognize(
        self,
        *,
        image_bytes: bytes,
        user_id: UUID,
        session: AsyncSession,
    ) -> tuple[Phase1Result, LLMCallResult | None]:
        """Распознать фото.

        Проверяет pHash-кэш. Если попадание — возвращает кэш и ``None``
        вместо LLMCallResult (API не вызывался, токены не потрачены).

        Returns:
            (Phase1Result, LLMCallResult | None)
        """
        phash = compute_phash(image_bytes)

        # --- pHash cache lookup ---
        cached = await self._find_cache(session, user_id=user_id, phash=phash)
        if cached is not None:
            log.info("vision.cache_hit", user_id=str(user_id), phash=phash)
            try:
                raw_items = json.loads(cached.items_json)
                items = [RecognizedItem.model_validate(i) for i in raw_items]
            except Exception as exc:
                log.warning("vision.cache_parse_error", error=str(exc))
                items = []
            overall = cached.overall_confidence if items else 0.0
            return Phase1Result(items=items, overall_confidence=overall, from_cache=True), None

        # --- Vision API ---
        llm_result = await self._client.call_vision(
            system=self._system,
            image_bytes=image_bytes,
            prompt="Identify all food items visible in this photo.",
            model=self._client.sonnet_model,
            max_tokens=1024,
        )

        items = _parse_items(llm_result.text)
        overall = (
            sum(i.confidence for i in items) / len(items) if items else 0.0
        )

        # --- Persist (photo_kept = false) ---
        recognition = PhotoRecognition(
            user_id=user_id,
            phash=phash,
            items_json=json.dumps([i.model_dump() for i in items], ensure_ascii=False),
            overall_confidence=overall,
            cost_cents=llm_result.cost_cents,
            llm_model=llm_result.model,
            photo_kept=False,
        )
        session.add(recognition)
        # Не коммитим здесь — хендлер коммитит после всего.

        return Phase1Result(items=items, overall_confidence=overall), llm_result

    async def _find_cache(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        phash: str,
    ) -> PhotoRecognition | None:
        """Ищет кэш-хит по pHash в пределах PHASH_CACHE_DAYS.

        Сначала пробует точное совпадение phash. Если нет — загружает последние
        записи пользователя и сравнивает Хэмминг в Python.
        """
        cutoff = datetime.now(tz=UTC) - timedelta(days=PHASH_CACHE_DAYS)

        # Быстрый путь: точное совпадение.
        exact_stmt = (
            select(PhotoRecognition)
            .where(PhotoRecognition.user_id == user_id)
            .where(PhotoRecognition.phash == phash)
            .where(PhotoRecognition.created_at >= cutoff)
            .order_by(PhotoRecognition.created_at.desc())
            .limit(1)
        )
        exact_row = await session.scalar(exact_stmt)
        if exact_row is not None:
            return exact_row

        # Медленный путь: загружаем последние 100 записей и считаем Хэмминг.
        recent_stmt = (
            select(PhotoRecognition)
            .where(PhotoRecognition.user_id == user_id)
            .where(PhotoRecognition.created_at >= cutoff)
            .order_by(PhotoRecognition.created_at.desc())
            .limit(100)
        )
        result = await session.execute(recent_stmt)
        for row in result.scalars():
            try:
                if phash_hamming(phash, row.phash) <= PHASH_DISTANCE_THRESHOLD:
                    return row
            except Exception:
                continue
        return None
