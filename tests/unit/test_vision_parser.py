"""Unit-тесты JSON-парсинга ответа Sonnet в VisionParser.

Не дёргаем Anthropic API — тестируем чистые функции _parse_items,
compute_phash, phash_hamming.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from src.agents.vision_phase1 import (
    VisionParseError,
    _parse_items,
    compute_phash,
    phash_hamming,
)

pytestmark = pytest.mark.unit


# ---- _parse_items ----


def test_parse_typical_response() -> None:
    raw = (
        '<json>[{"name_en":"chicken breast","name_ru":"куриная грудка",'
        '"grams_min":150,"grams_max":200,"confidence":0.88,"uncertain":false,'
        '"alternatives":[]}]</json>'
    )
    items = _parse_items(raw)
    assert len(items) == 1
    assert items[0].name_en == "chicken breast"
    assert items[0].name_ru == "куриная грудка"
    assert items[0].grams_min == 150
    assert items[0].grams_max == 200
    assert items[0].confidence == pytest.approx(0.88)
    assert items[0].uncertain is False
    assert items[0].grams_mid == 175


def test_parse_empty_array() -> None:
    assert _parse_items("<json>[]</json>") == []


def test_parse_multiple_items() -> None:
    raw = (
        "<json>["
        '{"name_en":"white rice","name_ru":"рис белый","grams_min":180,"grams_max":220,'
        '"confidence":0.92,"uncertain":false,"alternatives":[]},'
        '{"name_en":"fried egg","name_ru":"яичница","grams_min":50,"grams_max":70,'
        '"confidence":0.75,"uncertain":false,"alternatives":[]}'
        "]</json>"
    )
    items = _parse_items(raw)
    assert len(items) == 2
    assert items[0].name_en == "white rice"
    assert items[1].name_en == "fried egg"


def test_parse_skips_invalid_entry() -> None:
    """Bitaya запись (grams_min отрицательный) не должна валить весь батч."""
    raw = (
        "<json>["
        '{"name_en":"rice","name_ru":"рис","grams_min":150,"grams_max":200,'
        '"confidence":0.9,"uncertain":false,"alternatives":[]},'
        '{"name_en":"","name_ru":"","grams_min":-10,"grams_max":0,'  # invalid
        '"confidence":0.5,"uncertain":false,"alternatives":[]}'
        "]</json>"
    )
    items = _parse_items(raw)
    assert len(items) == 1
    assert items[0].name_en == "rice"


def test_parse_missing_block_raises() -> None:
    with pytest.raises(VisionParseError):
        _parse_items('[{"name_en":"rice"}]')


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(VisionParseError):
        _parse_items("<json>{broken</json>")


def test_parse_non_array_raises() -> None:
    with pytest.raises(VisionParseError):
        _parse_items('<json>{"name_en":"rice"}</json>')


def test_parse_handles_multiline_and_whitespace() -> None:
    raw = """
    Some preamble.
    <json>
    [{"name_en":"banana","name_ru":"банан","grams_min":100,"grams_max":130,
    "confidence":0.8,"uncertain":false,"alternatives":[]}]
    </json>
    """
    items = _parse_items(raw)
    assert len(items) == 1
    assert items[0].name_en == "banana"


def test_parse_uncertain_item_with_alternatives() -> None:
    raw = (
        "<json>["
        '{"name_en":"unknown sauce","name_ru":"соус неизвестный",'
        '"grams_min":20,"grams_max":40,"confidence":0.4,"uncertain":true,'
        '"alternatives":["ketchup","tomato sauce"]}'
        "]</json>"
    )
    items = _parse_items(raw)
    assert items[0].uncertain is True
    assert "ketchup" in items[0].alternatives


# ---- compute_phash / phash_hamming ----


def _make_solid_bytes(color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_gradient_bytes(start: int, end: int) -> bytes:
    """Горизонтальный градиент — даёт разные pHash для разных значений."""
    import numpy as np

    arr = np.zeros((64, 64, 3), dtype=np.uint8)
    for x in range(64):
        val = start + (end - start) * x // 63
        arr[:, x, 0] = val  # только R-канал
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_compute_phash_returns_hex_string() -> None:
    phash = compute_phash(_make_solid_bytes())
    assert isinstance(phash, str)
    assert len(phash) == 16
    assert all(c in "0123456789abcdef" for c in phash)


def test_same_image_same_phash() -> None:
    img = _make_solid_bytes()
    assert compute_phash(img) == compute_phash(img)


def test_different_images_different_phash() -> None:
    """Градиенты в разных направлениях дают разные pHash."""
    left_dark = _make_gradient_bytes(0, 255)
    right_dark = _make_gradient_bytes(255, 0)
    assert compute_phash(left_dark) != compute_phash(right_dark)


def test_phash_hamming_identical() -> None:
    img = _make_solid_bytes()
    h = compute_phash(img)
    assert phash_hamming(h, h) == 0


def test_phash_hamming_different_images() -> None:
    a = compute_phash(_make_gradient_bytes(0, 255))
    b = compute_phash(_make_gradient_bytes(255, 0))
    dist = phash_hamming(a, b)
    assert 0 <= dist <= 64


def test_phash_hamming_mismatched_length() -> None:
    assert phash_hamming("abcd", "abcdef") == 64
