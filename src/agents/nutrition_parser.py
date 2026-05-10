"""Nutrition text-input parser (Haiku 4.5).

Извлекает из текста «куриная грудка 200г, рис 150г» список объектов
``ParsedFoodEntry``. Используется в Orchestrator-роутинге и в
``/log``-handler-е бота.

Промпт лежит в ``src/agents/prompts/nutrition_parser.md`` — кэшируется
через ``cache_control: ephemeral``. Это даёт ~10× экономию при повторных
вызовах в течение 5-минутного окна.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from src.agents.client import ClaudeClient, LLMCallResult
from src.core.logging import get_logger
from src.domains.nutrition.schemas import ParsedFoodEntry

log = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "nutrition_parser.md"
_JSON_BLOCK_RE = re.compile(r"<json>\s*(.*?)\s*</json>", re.DOTALL)


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class NutritionParseError(RuntimeError):
    """Не удалось распарсить ответ модели."""


class NutritionParser:
    """Обёртка над Claude Haiku для извлечения food entries."""

    def __init__(self, client: ClaudeClient | None = None) -> None:
        self._client = client or ClaudeClient()
        self._system = _load_prompt()

    async def parse(self, user_text: str) -> tuple[list[ParsedFoodEntry], LLMCallResult]:
        """Распарсить пользовательский текст.

        Returns:
            (entries, llm_result). При пустом списке entries — пользователь
            не упомянул ничего съедобного (handler покажет «не понял»).

        Raises:
            NutritionParseError: модель вернула невалидный JSON или формат
                нарушает схему. Handler ловит и просит повторить ввод.
        """
        result = await self._client.call_text(
            system=self._system,
            user=user_text,
            model=self._client.haiku_model,
            max_tokens=512,
            temperature=0.0,
            cache_system=True,
        )
        entries = _parse_entries(result.text)
        return entries, result


def _parse_entries(raw: str) -> list[ParsedFoodEntry]:
    """Извлечь и валидировать `<json>[...]</json>`-блок."""
    match = _JSON_BLOCK_RE.search(raw)
    if match is None:
        raise NutritionParseError(f"missing <json> block in response: {raw!r}")

    payload = match.group(1).strip()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise NutritionParseError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise NutritionParseError(f"expected JSON array, got {type(data).__name__}")

    entries: list[ParsedFoodEntry] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise NutritionParseError(f"entry #{i} is not an object")
        try:
            entries.append(ParsedFoodEntry.model_validate(item))
        except ValidationError as exc:
            log.warning("nutrition_parser.invalid_entry", index=i, item=item, error=str(exc))
            # Не валим весь батч — пропускаем некорректную запись.
            continue
    return entries
