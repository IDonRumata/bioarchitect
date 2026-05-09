# BioArchitect

**AI Wellness Companion for Drivers & Shift Workers**

Персональный AI-ассистент по питанию, лабораторным показателям и дневнику самочувствия. Работает на смартфоне (Telegram → Mini App → PWA → Android APK), без специального железа. Адаптирован для дальнобойщиков EU/СНГ и вахтовых работников.

> **Правовой статус:** Wellness-сервис и образовательный справочник. Не является медицинским устройством (EU MDR Art. 2(1) intended-purpose exemption). Не интерпретирует личные медицинские данные.

## Roadmap платформ

| Канал | Срок | Технология |
|---|---|---|
| Telegram Bot | Месяц 1 | aiogram 3.x |
| Telegram Mini App | Месяц 2 | React + Vite + WebApp SDK |
| PWA | Месяц 3 | React + manifest |
| Android APK | Месяц 4 | Capacitor.js |
| Google Play / App Store | Месяц 6+ | Capacitor bundle |

## Ключевые конкурентные преимущества

- В 2.5–4.5× дешевле Whoop / Fitbit Air
- Работает на смартфоне, который уже есть (без железа)
- Единственная база КБЖУ заправок EU/СНГ (100+ сетей: Aral, Orlen, Shell, McDonald's, Lidl…)
- OCR анализов крови (отсутствует у конкурентов)
- Telegram-first: работает в РФ/BY/KZ без Google/Apple
- GDPR-compliant: удаление одной кнопкой, серверы только в EU

## Тарифы

| Тариф | Цена | Vision/день | OCR/мес | LLM запросов/день |
|---|---|---|---|---|
| FREE | $0 | 1 | — | 5 |
| PRO | $79/год | 15 | 5 | 50 |
| PRO+ | $149/год | 30 | 20 | 150 |
| FLEET (B2B) | $5/водитель/мес | 15 | 5 | 50 |

## Технологический стек

- **Backend:** Python 3.12 + aiogram 3 + FastAPI + SQLAlchemy 2 + Alembic
- **БД:** PostgreSQL 16 + pgvector + pg_partman
- **Кэш / очереди:** Redis 7 + ARQ
- **LLM:** Anthropic Claude (Haiku 4.5 + Sonnet 4.6) с Prompt Caching
- **Frontend:** React + TypeScript + Vite + Tailwind + Capacitor.js
- **Контейнеры:** Docker Compose + Traefik v3
- **Мониторинг:** Sentry + Prometheus + Grafana + Loki
- **Платежи:** Telegram Stars + Stripe + ЮKassa
- **Secrets:** sops + age (планируется)

> Запрещено в проекте: LangChain / LangGraph / CrewAI, OpenAI API, Supabase, Kubernetes, AdMob, Pinecone / Qdrant.

## Документация

- [`CLAUDE.md`](CLAUDE.md) — системный промпт для Claude Code
- [`BRIEF.md`](BRIEF.md) — текущий статус проекта (источник истины между сессиями)
- [`docs/TZ.md`](docs/TZ.md) — полное техзадание v1.2
- [`docs/architecture-decisions/`](docs/architecture-decisions/) — ADR-файлы

## Разработка

```bash
# Локальная разработка
make dev                # запустить postgres + redis + bot + api в Docker
make migrate            # применить миграции БД
make test               # unit-тесты
make eval               # eval suite Censor Agent (CI gate)
make lint               # ruff + mypy
make seed               # засеять USDA + Open Food Facts + base chains
```

## Структура репозитория

См. [`docs/architecture-decisions/0001-monorepo-layout.md`](docs/architecture-decisions/0001-monorepo-layout.md) и Приложение А ТЗ.

## Лицензия

Proprietary. © 2026 BioArchitect. Все права защищены.
