"""Единый клиент Anthropic SDK.

Все вызовы к Claude идут через этот клиент. Это даёт нам:
    - Prompt Caching по умолчанию (cache_control: ephemeral на system).
    - Retry с экспоненциальным backoff на 429 / 5xx.
    - Подсчёт ``cost_cents`` (логируется в structlog; полная таблица
      ``llm_calls`` появится в спринте 7).
    - Тайминги для p95-метрик.

ВАЖНО: OpenAI SDK / LangChain / любые обёртки запрещены (CLAUDE.md §2.1).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic

import anthropic
from anthropic import APIStatusError, AsyncAnthropic, RateLimitError

from src.core.config import get_settings
from src.core.logging import get_logger

log = get_logger(__name__)


# Прайс-лист Claude (USD за 1M токенов). Обновлять при релизе моделей.
# Источник: https://www.anthropic.com/pricing — May 2026.
_PRICING_USD_PER_MTOK: dict[str, dict[str, float]] = {
    # Haiku 4.5
    "claude-haiku-4-5": {
        "input": 1.0,
        "output": 5.0,
        "cache_write": 1.25,
        "cache_read": 0.10,
    },
    # Sonnet 4.6
    "claude-sonnet-4-6": {
        "input": 3.0,
        "output": 15.0,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
}


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
    latency_ms: int


def _compute_cost_cents(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
) -> float:
    """Стоимость в центах. Если модель неизвестна — 0 (с warning в логе)."""
    rates = _PRICING_USD_PER_MTOK.get(model)
    if rates is None:
        log.warning("client.unknown_model_pricing", model=model)
        return 0.0
    usd = (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_creation_tokens * rates["cache_write"]
        + cache_read_tokens * rates["cache_read"]
    ) / 1_000_000
    return round(usd * 100, 4)


class ClaudeClient:
    """Тонкая обёртка над Anthropic SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.anthropic_api_key.get_secret_value()
        if not api_key:
            log.warning("client.no_api_key", hint="Set ANTHROPIC_API_KEY in .env")
        self._client = AsyncAnthropic(api_key=api_key)
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

    async def call_text(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        cache_system: bool = True,
        max_retries: int = 3,
    ) -> LLMCallResult:
        """Текстовый вызов Claude.

        Args:
            system: Системный промпт. По умолчанию помечается
                ``cache_control: ephemeral`` — повторные запросы с тем же
                ``system`` оплачиваются по льготному тарифу cache_read
                (~10× дешевле input). 5-min TTL.
            user: Пользовательский turn (одна реплика).
            model: ID модели. По умолчанию — haiku.
            cache_system: True → ставим cache_control на system.
            max_retries: количество ретраев на 429 / 5xx с экспонентой.

        Raises:
            anthropic.APIError: после исчерпания ретраев пробрасываем.
        """
        chosen_model = model or self._haiku
        use_cache = cache_system and self._cache_enabled and bool(system)

        # Система передаётся как список блоков, чтобы можно было приклеить
        # cache_control. Без списка SDK не пропустит cache_control.
        system_blocks: list[dict[str, object]] | str
        if use_cache:
            system_blocks = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_blocks = system

        attempt = 0
        last_exc: Exception | None = None
        started = monotonic()

        while attempt <= max_retries:
            try:
                response = await self._client.messages.create(
                    model=chosen_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_blocks,  # type: ignore[arg-type]
                    messages=[{"role": "user", "content": user}],
                )
                break
            except (RateLimitError, APIStatusError) as exc:
                last_exc = exc
                # 4xx (кроме 429) — не ретраим: это баг запроса.
                status = getattr(exc, "status_code", None)
                if isinstance(exc, APIStatusError) and status is not None and 400 <= status < 500 and status != 429:
                    raise
                if attempt == max_retries:
                    raise
                delay = 2**attempt
                log.warning(
                    "client.retry",
                    attempt=attempt + 1,
                    delay_s=delay,
                    error=str(exc),
                )
                await asyncio.sleep(delay)
                attempt += 1
        else:
            assert last_exc is not None
            raise last_exc

        latency_ms = int((monotonic() - started) * 1000)

        # Извлекаем текст. Для text-only ожидаем один TextBlock.
        text_parts: list[str] = []
        for block in response.content:
            if isinstance(block, anthropic.types.TextBlock):
                text_parts.append(block.text)
        text = "".join(text_parts)

        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0

        cost_cents = _compute_cost_cents(
            model=chosen_model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
        )

        log.info(
            "client.call_text",
            model=chosen_model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read=cache_read,
            cache_creation=cache_creation,
            cost_cents=cost_cents,
            latency_ms=latency_ms,
        )

        return LLMCallResult(
            text=text,
            model=chosen_model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            cost_cents=cost_cents,
            latency_ms=latency_ms,
        )
