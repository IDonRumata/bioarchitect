# BRIEF.md — Источник истины проекта BioArchitect

> Этот файл — единая точка правды между сессиями Claude Code. Обновляется в КОНЦЕ каждой сессии. Если ты Claude Code — прочитай этот файл ПЕРВЫМ.

---

## Текущий статус (2026-05-09)

**Спринт:** 0 (preparation / scaffolding).
**Завершено:** Создан репозиторий, базовый каркас монорепозитория (Variant A из плана подготовки).
**Следующий шаг:** Спринт 1 — `make dev` поднимает Postgres + Redis локально, аиограм skeleton принимает `/start`.

---

## 1. Аккаунты и доступы (что есть / чего нет)

| Что | Статус | Кто владеет | Где хранится |
|---|---|---|---|
| GitHub `IDonRumata/bioarchitect` | ✅ создан | Андрей | github.com |
| GitHub Personal Access Token | ✅ есть | Андрей | у него локально |
| Anthropic API key | ✅ есть | Андрей | console.anthropic.com |
| Telegram Bot Token | ✅ есть | Андрей | @BotFather |
| VPS Zomro (есть, NL?) | ⚠️ уточнить регион | Андрей | zomro.com |
| VPS Beget | ✅ есть, **НЕ для EU-данных** (RU) | Андрей | beget.com |
| Hetzner DE | ❌ нет | — | — |
| Stripe | ❌ нет | — | — |
| Telegram Stars (мерчант) | ❌ нет | — | через @BotFather |
| ЮKassa | ❌ нет | — | — |
| Backblaze B2 EU | ❌ нет | — | — |
| Sentry | ❌ нет | — | — |
| PostHog self-hosted | ❌ нет | — | — |
| DPA с Anthropic | ❌ не запрошен | — | privacy@anthropic.com |
| Медэдвайзер (нутрициолог + врач) | ❌ ищет Андрей | — | — |
| Юрист health/data privacy EU | ❌ нет | — | — |

## 2. Принятые решения

| Дата | Решение | Обоснование |
|---|---|---|
| 2026-05-09 | Папка проекта: `D:\Claude Code doc\Projects\bioarchitect\` | согласовано с владельцем |
| 2026-05-09 | Имя репо: `bioarchitect` | согласовано |
| 2026-05-09 | На MVP — НЕ реализуем Faster R-CNN reference object detection. Заглушка `WeightEstimate.source = "visual_estimate"` всегда. Реализация в v2.0. | избегаем 2-3 недель ML-работы, vision API + эталон в кадре проще |
| 2026-05-09 | Языки на старте: RU, EN, PL, DE | расширение охвата водителей EU |
| 2026-05-09 | База заправок: автоматизированный пайплайн парсинга PDF (а не ручной сидинг) | масштабируется до 100+ сетей без переписывания |
| 2026-05-09 | На старте production VPS — Zomro NL (если регион EU) или Hetzner DE | оба GDPR-compliant, выбор отложен до момента деплоя |
| 2026-05-09 | Recovery Index формула — детерминированный код, **clamp компонентов в [0, max]** чтобы избежать отрицательных значений при экстремальных данных | защита от багов |
| 2026-05-09 | Secrets: sops + age (не doppler, не .env в git) | бесплатно, audit trail в git, GDPR-friendly |

## 3. Блокеры и open questions

- [ ] **DPA с Anthropic** — без него юридически нельзя обрабатывать health-данные EU-пользователей в продакшне. Шаблон email подготовлен в `docs/legal/dpa-request-template.md` (TODO).
- [ ] **Медэдвайзер** — без него блокированы:
  - Eval suite Censor Agent (80+ кейсов нужны до релиза монетизации, спринт 7-8).
  - Lab reference ranges (без подписи `verified_by` модуль OCR анализов нельзя выпускать).
  - Образовательный RAG-контент (статьи требуют верификации врачом).
- [ ] **Embedding-модель для RAG.** OpenAI запрещён политикой проекта. Варианты:
  - Voyage AI `voyage-3-lite` (платный, EU-ready).
  - Self-hosted `bge-m3` или `e5-multilingual` через `sentence-transformers` (бесплатно, но требует ресурсов на VPS).
  - Решение откладывается до спринта 9 (RAG Agent).
- [ ] **EU MDR Art. 2(1)** intended-purpose claim — до релиза PRO нужен короткий юридический ревью ($300-500 в EU).
- [ ] **Регион VPS Zomro** — уточнить у Андрея, в каком ДЦ (NL подходит, RU — нет для EU-юзеров).
- [ ] **n8n** — упоминается в ТЗ для квартального обновления базы заправок, но не в стеке. Решение: используем ARQ workers с cron-расписанием (ARQ уже в стеке, лишний сервис не нужен).
- [ ] **Push-уведомления для APK без Google Play** — FCM требует Play Services. Решение: для РФ-аудитории на APK — только Telegram-нотификации; для PWA — WebPush.

## 4. Резолвенные проблемы (для истории)

_(пусто — ещё нет резолвенных проблем)_

## 5. Текущий план спринтов

| Спринт | Недели | Цель | Статус |
|---|---|---|---|
| 0 | — | Скаффолдинг репозитория | ✅ done |
| 1 | 1–2 | Docker Compose, Postgres + pgvector, Alembic init, aiogram `/start`, базовая FSM-структура | ⏭️ next |
| 2 | 3–4 | Онбординг FSM 5 шагов, GDPR-согласие, таблицы users/profiles/consents | ⏳ |
| 3 | 5–6 | Сидинг USDA + Open Food Facts, ручной ввод (Haiku) | ⏳ |
| 4 | 7–8 | Vision Phase 1 (распознавание + редактирование), pHash-кэш | ⏳ |
| 5 | 9–10 | Vision Phase 2 (chain DB + visual range), кнопки ±10г, daily check-in, Recovery Index | ⏳ |
| 6 | 11–12 | IF-трекер, Coach Agent | ⏳ |
| 7 | 13–14 | Censor Agent + eval suite, Stripe + Telegram Stars, paywall | ⏳ |
| 8 | 15–16 | RAG Agent + 30 статей, база заправок (топ-30 EU/СНГ) | ⏳ |
| 9 | 17–20 | React Mini App (Recovery + питание + IF), PWA manifest | ⏳ |
| 10 | 21–24 | OCR Lab Agent, lab markers, расширение базы заправок до 100+ | ⏳ |
| 11 | 25–28 | Capacitor APK, ЮKassa, Fleet B2B кабинет (базовый) | ⏳ |

## 6. Контакты владельца

- **Имя:** Андрей Мароз
- **GitHub:** IDonRumata
- **Локация:** Беларусь, дальнобойщик (rotates EU)
- **Стиль работы:** non-technical, нужны конкретные команды и пояснения по-русски, не теория
- **Среда:** Windows 11 (PowerShell), Git Bash; работает с проектом локально, деплой — SSH к VPS

## 7. Где что лежит

- ТЗ полное: `docs/TZ.md`
- Системный промпт Claude Code: `CLAUDE.md`
- ADR (архитектурные решения): `docs/architecture-decisions/`
- Eval suite Censor: `tests/agents/censor/`
- Промпты агентов: `src/agents/prompts/`
- Миграции БД: `alembic/versions/`
- Сидинг: `scripts/seed_*.py`
- Локализация: `locale/{ru,en,pl,de}/LC_MESSAGES/`
- Инфра: `infra/{prometheus,grafana,backup}/`

## 8. Шпаргалка команд

```bash
# Локальная разработка
make dev              # запустить postgres + redis + bot + api в Docker
make migrate          # alembic upgrade head
make migrate-new m="add_xyz"  # создать миграцию
make test             # pytest
make eval             # eval suite Censor (CI-gate)
make lint             # ruff check + mypy --strict
make format           # ruff format
make seed             # засеять справочники

# Git
git status
git checkout -b feat/sprint-1-onboarding
git commit -m "feat: ..."
git push -u origin feat/sprint-1-onboarding
```
