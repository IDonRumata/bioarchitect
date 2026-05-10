"""Unit-тесты JSON-парсинга ответа Haiku в NutritionParser.

Не дёргаем Anthropic API — тестируем чистый парсер _parse_entries.
"""

from __future__ import annotations

import pytest

from src.agents.nutrition_parser import NutritionParseError, _parse_entries


def test_parse_typical_response() -> None:
    raw = '<json>[{"query":"куриная грудка","grams":200},{"query":"рис","grams":150}]</json>'
    entries = _parse_entries(raw)
    assert len(entries) == 2
    assert entries[0].query == "куриная грудка"
    assert entries[0].grams == 200
    assert entries[1].query == "рис"
    assert entries[1].grams == 150


def test_parse_empty_array() -> None:
    raw = "<json>[]</json>"
    assert _parse_entries(raw) == []


def test_parse_skips_invalid_entries() -> None:
    """Битая запись не должна валить весь батч."""
    raw = (
        '<json>[{"query":"рис","grams":150},'
        '{"query":"","grams":100},'           # пустой query — отвалится pydantic
        '{"query":"кефир","grams":200}]</json>'
    )
    entries = _parse_entries(raw)
    assert [e.query for e in entries] == ["рис", "кефир"]


def test_parse_missing_block_raises() -> None:
    with pytest.raises(NutritionParseError):
        _parse_entries('[{"query":"рис","grams":150}]')


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(NutritionParseError):
        _parse_entries("<json>{broken</json>")


def test_parse_non_array_raises() -> None:
    with pytest.raises(NutritionParseError):
        _parse_entries('<json>{"query":"рис","grams":150}</json>')


def test_parse_handles_multiline_and_whitespace() -> None:
    raw = """
    Some preamble that the model shouldn't add but might.
    <json>
    [{"query":"banana","grams":120}]
    </json>
    """
    entries = _parse_entries(raw)
    assert len(entries) == 1
    assert entries[0].query == "banana"
    assert entries[0].grams == 120
