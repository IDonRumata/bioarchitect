"""Точка входа FastAPI-приложения.

Запуск:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.core.safety import assert_safe_to_start

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    assert_safe_to_start()
    settings = get_settings()
    log.info("api.started", env=settings.env.value)
    yield
    log.info("api.stopped")


app = FastAPI(
    title="BioArchitect API",
    version="0.1.0",
    description="Internal API + payment webhooks + Telegram webhook.",
    lifespan=lifespan,
)


@app.get("/health", tags=["meta"])
async def health() -> JSONResponse:
    """Liveness probe для Docker / Traefik."""
    return JSONResponse({"status": "ok"})


@app.get("/ready", tags=["meta"])
async def ready() -> JSONResponse:
    """Readiness probe — проверяет БД и Redis (TODO sprint 1)."""
    return JSONResponse({"status": "ok", "checks": {"db": "todo", "redis": "todo"}})
