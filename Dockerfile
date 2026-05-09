# =============================================================================
# BioArchitect — multi-stage Dockerfile
# Этапы:
#   1. base       — Python 3.12, uv, системные зависимости
#   2. deps       — установка зависимостей из pyproject.toml
#   3. builder    — копирование кода
#   4. dev        — образ для локальной разработки (hot-reload)
#   5. production — slim-образ для продакшна
# =============================================================================

ARG PYTHON_VERSION=3.12.7

# ---------- Этап 1: base ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Системные зависимости:
#   libpq5         — runtime для asyncpg
#   build-essential, libpq-dev — для компиляции psycopg при необходимости
#   tini           — корректный PID 1
#   curl           — healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        build-essential \
        libpq-dev \
        tini \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv — установка
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

WORKDIR /app

# ---------- Этап 2: deps ----------
FROM base AS deps

COPY pyproject.toml ./
COPY uv.lock* ./

# Виртуалка в /app/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev || \
    uv sync --no-install-project --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# ---------- Этап 3: builder ----------
FROM deps AS builder
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
COPY locale ./locale

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev || uv sync --no-dev

# ---------- Этап 4: dev ----------
FROM base AS dev

COPY --from=deps /app/.venv /app/.venv
COPY pyproject.toml ./
COPY uv.lock* ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --all-extras || uv sync --all-extras

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

EXPOSE 8000 9090

# В dev tini не критичен — оставляем для единообразия
ENTRYPOINT ["/usr/bin/tini", "--"]
# Команда переопределяется через docker-compose
CMD ["python", "-m", "src.bot.main"]

# ---------- Этап 5: production ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        tini \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app -g 1000 \
    && useradd -r -g app -u 1000 -d /app -s /sbin/nologin app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src
COPY --from=builder --chown=app:app /app/alembic /app/alembic
COPY --from=builder --chown=app:app /app/alembic.ini /app/alembic.ini
COPY --from=builder --chown=app:app /app/locale /app/locale

USER app

EXPOSE 8000 9090

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "src.bot.main"]
