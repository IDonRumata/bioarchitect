"""Единый клиент Anthropic SDK.

Все вызовы к Claude идут через этот клиент. Это даёт нам:
    - Prompt Caching по умолчанию (cache_control: ephemeral)
    - Retry с экспоненциальным backoff
    - Логирование cost_cents в llm_calls
    - Тайминги для p95-метрик

ВАЖНО: OpenAI SDK / LangChain / любые обёртки запрещены.
"""

from __future__ import annotations

from dataclasses import dataclass

from anthropic import AsyncAnthropic

from src.core.config import get_settings
from src.core.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class LLMCallResult:
    """Результат одного вызова Claude."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_cents: float


class ClaudeClient:
    """Тонкая обёртка над Anthropic SDK.

    Будет дополнена в спринте 3-4 (когда понадобятся первые LLM-вызовы):
        - retry с backoff (anthropic._exceptions.APIStatusError)
        - prompt caching на системные промпты
        - логирование в llm_calls
        - rate limiting через Redis
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
        )
        self._haiku = settings.anthropic_model_haiku
        self._sonnet = settings.anthropic_model_sonnet
        self._cache_enabled = settings.anthropic_prompt_cache

    @property
    def haiku_model(self) -> str:
        return self._haiku

    @property
    def sonnet_model(self) -> str:
        return self._sonnet

    @property
    def cache_enabled(self) -> bool:
        return self._cache_enabled

    # TODO(sprint-3): метод call_text(system, user, model) -> LLMCallResult
    # TODO(sprint-4): метод call_vision(system, image_bytes, prompt) -> LLMCallResult
    # TODO(sprint-7): полный аудит в llm_calls
