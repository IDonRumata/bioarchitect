# BRIEF.md — Источник истины проекта BioArchitect

> Этот файл — единая точка правды между сессиями Claude Code. Обновляется в КОНЦЕ каждой сессии. Если ты Claude Code — прочитай этот файл ПЕРВЫМ.

---

## Текущий статус (2026-05-10)

**Спринт:** 1 (онбординг + GDPR-согласие) — **завершён**.

**Завершено:**
- Спринт 0 — каркас монорепозитория, 114 файлов, 5 ADR, шаблон DPA.
- Спринт 1 — модели `users` / `user_profiles` / `consent_records` + первая миграция Alembic, репозитории + сервисы (`UserService`, `ConsentService`), `DBSessionMiddleware` + `I18nMiddleware`, FSM-онбординг 8 шагов (GDPR Art. 9 → 5 этапов из ТЗ §5.1), 4 `.po`-файла локалей (заглушки), unit-тесты Pydantic-валидации payload + версии согласий + smoke-импорт всех модулей.

**Следующий шаг:** Спринт 2 — обёртка handler-строк в `_()` (gettext flow), главное меню, команда `/profile`, soft-delete handler, ARQ воркер `data_deletion_processor` для hard-delete после grace period 30 дней.

**Перед стартом Спринта 2 нужно от Андрея:**
1. Установить Docker Desktop + uv, склонировать репо, создать `.env` (см. `docs/setup/local-development.md`).
2. Запустить `make dev` — убедиться что postgres + redis + bot + api поднимаются.
3. Запустить `make migrate` — должна применится миграция `20260509_1200_initial_schema`.
4. Открыть бота в Telegram → `/start` → пройти онбординг — убедиться что вся FSM работает end-to-end.
5. Если всё ок — переходим в спринт 2.

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
| 2026-05-10 | `birth_year` вместо полной даты (GDPR Data Minimization). Минимум 18+ через CHECK constraint и валидацию FSM. | соответствует ТЗ §5.1 + Censor blocklist (н/л запрещены) |
| 2026-05-10 | Pattern: append-only `consent_records`. Отзыв = новая строка `granted=false`. Никаких UPDATE. | GDPR audit trail требует полную историю |
| 2026-05-10 | IP в `consent_records` хранится как sha256 хеш с солью, а не raw. | Data Minimization, но достаточно для proof-of-consent |

## 3. Блокеры и open questions

- [ ] **DPA с Anthropic** — без него юридически нельзя обрабатывать health-данные EU-пользователей в продакшне. Шаблон email готов в `docs/legal/dpa-request-template.md` — Андрею отправить с своей почты.
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

- **2026-05-10 — спринт 1.** Hardcoded RU-строки в `src/bot/handlers/onboarding.py` не обёрнуты в `_()`. Принято решение: на старте RU — `default_locale`, остальные языки приходят к спринту 2 вместе с обёрткой строк через `make i18n-extract` → `make i18n-update` → перевод PL/DE. `.po`-файлы созданы как заглушки. Это не блокер для запуска бота на RU.
- **2026-05-10 — спринт 1.** В `consent_records` снапшот `version` документа — на момент согласия. Если бампим `CONSENT_VERSIONS["health_data_processing"]` с `1.0` на `2.0` — `has_active_consent` для пользователей со старой версией вернёт `False`, и Censor / приложение запросят повторное согласие. Это намеренное поведение GDPR-compliance.

## 5. Текущий план спринтов

| Спринт | Недели | Цель | Статус |
|---|---|---|---|
| 0 | — | Скаффолдинг репозитория | ✅ done |
| 1 | 1–2 | Docker Compose, Postgres, Alembic, FSM-онбординг 8 шагов (GDPR + 5 этапов), таблицы users/profiles/consents | ✅ done |
| 2 | 3–4 | i18n-обёртка `_()`, главное меню, `/profile`, soft-delete + ARQ hard-delete воркер, /settings | ⏭️ next |
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
