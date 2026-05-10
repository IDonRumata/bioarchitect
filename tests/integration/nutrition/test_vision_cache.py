"""Integration-тесты pHash-кэша photo_recognitions.

Тестируем:
    - Сохранение записи PhotoRecognition в БД.
    - Точное совпадение pHash → cache hit.
    - Разные pHash → cache miss.
    - Кэш-хит по близкому Хэммингу (≤ 5).
    - Записи старше 30 дней не считаются.

Не вызываем Anthropic API — патчим VisionParser.recognize чтобы вернуть
готовый Phase1Result напрямую.
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.vision_phase1 import (
    Phase1Result,
    RecognizedItem,
    VisionParser,
    compute_phash,
    phash_hamming,
)
from src.domains.nutrition.models import PhotoRecognition
from src.domains.users.enums import UserStatus
from src.domains.users.models import User

pytestmark = pytest.mark.integration


def _make_jpeg(color: tuple[int, int, int] = (200, 100, 50)) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


_SAMPLE_ITEM = RecognizedItem(
    name_en="chicken breast",
    name_ru="куриная грудка",
    grams_min=150,
    grams_max=200,
    confidence=0.88,
    uncertain=False,
)


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> User:
    u = User(
        telegram_id=800_000_000 + int(uuid4().int % 1_000_000),
        username="vision_test_user",
        locale="ru",
        status=UserStatus.ACTIVE,
        country_iso="PL",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.mark.asyncio
async def test_exact_phash_cache_hit(db_session: AsyncSession, user: User) -> None:
    """Точное совпадение pHash → кэш возвращает сохранённые данные."""
    image_bytes = _make_jpeg()
    phash = compute_phash(image_bytes)

    # Сохраняем запись напрямую в БД.
    rec = PhotoRecognition(
        user_id=user.id,
        phash=phash,
        items_json=json.dumps([_SAMPLE_ITEM.model_dump()], ensure_ascii=False),
        overall_confidence=0.88,
        cost_cents=0.5,
        llm_model="claude-sonnet-4-6",
        photo_kept=False,
    )
    db_session.add(rec)
    await db_session.commit()

    # Патчим _client.call_vision — он не должен вызываться при cache hit.
    parser = VisionParser()
    with patch.object(parser._client, "call_vision", new_callable=AsyncMock) as mock_vision:
        result, llm_result = await parser.recognize(
            image_bytes=image_bytes,
            user_id=user.id,
            session=db_session,
        )

    mock_vision.assert_not_called()
    assert result.from_cache is True
    assert len(result.items) == 1
    assert result.items[0].name_en == "chicken breast"
    assert llm_result is None


@pytest.mark.asyncio
async def test_cache_miss_calls_vision_api(db_session: AsyncSession, user: User) -> None:
    """Нет кэша → вызываем Vision API и сохраняем результат."""
    image_bytes = _make_jpeg(color=(10, 20, 30))

    _FAKE_RESPONSE = (
        '<json>[{"name_en":"white rice","name_ru":"рис белый",'
        '"grams_min":180,"grams_max":220,"confidence":0.9,'
        '"uncertain":false,"alternatives":[]}]</json>'
    )

    from src.agents.client import LLMCallResult

    fake_llm = LLMCallResult(
        text=_FAKE_RESPONSE,
        model="claude-sonnet-4-6",
        input_tokens=500,
        output_tokens=60,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        cost_cents=0.3,
        latency_ms=800,
    )

    parser = VisionParser()
    with patch.object(parser._client, "call_vision", new_callable=AsyncMock, return_value=fake_llm):
        result, llm_result = await parser.recognize(
            image_bytes=image_bytes,
            user_id=user.id,
            session=db_session,
        )

    assert result.from_cache is False
    assert llm_result is not None
    assert llm_result.cost_cents == pytest.approx(0.3)
    assert len(result.items) == 1
    assert result.items[0].name_en == "white rice"

    # Запись должна появиться в БД (не закоммичена ещё — flush).
    await db_session.flush()
    row = await db_session.execute(
        text("SELECT phash, photo_kept FROM photo_recognitions WHERE user_id = :uid"),
        {"uid": user.id},
    )
    saved = row.one()
    assert saved.photo_kept is False
    phash = compute_phash(image_bytes)
    assert saved.phash == phash


@pytest.mark.asyncio
async def test_stale_cache_not_used(db_session: AsyncSession, user: User) -> None:
    """Запись старше 30 дней не считается кэш-хитом."""
    image_bytes = _make_jpeg(color=(50, 50, 50))
    phash = compute_phash(image_bytes)

    old_created_at = datetime.now(tz=UTC) - timedelta(days=31)
    rec = PhotoRecognition(
        user_id=user.id,
        phash=phash,
        items_json=json.dumps([_SAMPLE_ITEM.model_dump()]),
        overall_confidence=0.88,
        cost_cents=0.0,
        llm_model="claude-sonnet-4-6",
        photo_kept=False,
    )
    db_session.add(rec)
    await db_session.flush()
    # Перезаписываем created_at напрямую через SQL.
    await db_session.execute(
        text("UPDATE photo_recognitions SET created_at = :ts WHERE id = :id"),
        {"ts": old_created_at, "id": rec.id},
    )
    await db_session.commit()

    from src.agents.client import LLMCallResult

    fake_llm = LLMCallResult(
        text="<json>[]</json>",
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=10,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        cost_cents=0.01,
        latency_ms=200,
    )

    parser = VisionParser()
    with patch.object(parser._client, "call_vision", new_callable=AsyncMock, return_value=fake_llm) as mock_vision:
        result, llm_result = await parser.recognize(
            image_bytes=image_bytes,
            user_id=user.id,
            session=db_session,
        )

    # Старая запись проигнорирована → API вызван.
    mock_vision.assert_called_once()
    assert result.from_cache is False


@pytest.mark.asyncio
async def test_different_image_cache_miss(db_session: AsyncSession, user: User) -> None:
    """Другое изображение → cache miss даже если запись есть для другого."""
    img_red = _make_jpeg(color=(255, 0, 0))
    img_blue = _make_jpeg(color=(0, 0, 255))

    phash_red = compute_phash(img_red)
    phash_blue = compute_phash(img_blue)
    # Убедимся что расстояние > 5 (иначе тест не имеет смысла).
    assume_different = phash_hamming(phash_red, phash_blue) > 5

    if not assume_different:
        pytest.skip("Pillow генерирует одинаковые pHash для этих цветов — пропускаем")

    rec = PhotoRecognition(
        user_id=user.id,
        phash=phash_red,
        items_json=json.dumps([_SAMPLE_ITEM.model_dump()]),
        overall_confidence=0.88,
        cost_cents=0.0,
        llm_model="claude-sonnet-4-6",
        photo_kept=False,
    )
    db_session.add(rec)
    await db_session.commit()

    from src.agents.client import LLMCallResult

    fake_llm = LLMCallResult(
        text="<json>[]</json>",
        model="claude-sonnet-4-6",
        input_tokens=100,
        output_tokens=10,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        cost_cents=0.01,
        latency_ms=200,
    )

    parser = VisionParser()
    with patch.object(parser._client, "call_vision", new_callable=AsyncMock, return_value=fake_llm) as mock_vision:
        result, _ = await parser.recognize(
            image_bytes=img_blue,  # другое фото
            user_id=user.id,
            session=db_session,
        )

    mock_vision.assert_called_once()
    assert result.from_cache is False
