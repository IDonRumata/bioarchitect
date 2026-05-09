"""Redis-клиент для кэша, rate limiting и pub/sub."""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis, from_url

from src.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    """Singleton Redis-клиент."""
    settings = get_settings()
    return from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
