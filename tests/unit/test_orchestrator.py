"""Unit-тесты Orchestrator.classify_text."""

from __future__ import annotations

import pytest

from src.agents.orchestrator import IntentType, Orchestrator

pytestmark = pytest.mark.unit


@pytest.fixture
def orch() -> Orchestrator:
    return Orchestrator()


@pytest.mark.parametrize(
    "text",
    [
        "куриная грудка 200г",
        "рис 150 гр и кефир 200мл",  # мл нет в pattern, но «150 гр» сработает
        "2 яйца",
        "1kg potatoes",
        "Hähnchenbrust 250g",
        "100 грамм творога",
        "0.5 кг яблок",
    ],
)
def test_nutrition_text_high_confidence(orch: Orchestrator, text: str) -> None:
    intent = orch.classify_text(text)
    assert intent.type == IntentType.NUTRITION_TEXT
    assert intent.confidence >= 0.9


@pytest.mark.parametrize(
    "text",
    [
        "съел курицу с рисом",
        "ate a banana",
        "jadłem śniadanie",
        "habe Frühstück gegessen",
    ],
)
def test_nutrition_text_fallback(orch: Orchestrator, text: str) -> None:
    intent = orch.classify_text(text)
    assert intent.type == IntentType.NUTRITION_TEXT
    assert 0.5 <= intent.confidence < 0.9


@pytest.mark.parametrize(
    "text",
    [
        "как дела?",
        "что такое recovery index?",
        "why am I tired?",
    ],
)
def test_question(orch: Orchestrator, text: str) -> None:
    intent = orch.classify_text(text)
    assert intent.type == IntentType.QUESTION


@pytest.mark.parametrize("text", ["", "   ", "ok"])
def test_unknown(orch: Orchestrator, text: str) -> None:
    intent = orch.classify_text(text)
    assert intent.type == IntentType.UNKNOWN
