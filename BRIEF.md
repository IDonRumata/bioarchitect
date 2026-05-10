# BRIEF.md — Источник истины проекта BioArchitect

> Этот файл — единая точка правды между сессиями Claude Code. Обновляется в КОНЦЕ каждой сессии. Если ты Claude Code — прочитай этот файл ПЕРВЫМ.

---

## Текущий статус (2026-05-10)

**Спринт:** 4 — Vision Phase 1 — **завершён**.

**Завершено:**
- Спринт 0 — каркас монорепозитория, 114 файлов, 5 ADR, шаблон DPA.
- Спринт 1 — модели `users` / `user_profiles` / `consent_records` + первая миграция Alembic, репозитории + сервисы (`UserService`, `ConsentService`), `DBSessionMiddleware` + `I18nMiddleware`, FSM-онбординг 8 шагов (GDPR Art. 9 → 5 этапов из ТЗ §5.1), unit-тесты Pydantic-валидации.
- Спринт 2 — главное меню (ReplyKeyboardMarkup), хендлеры `/profile` (read-only сводка), `/settings` (переключатель языка), `/delete` (soft-delete с подтверждением + кнопка undo в течение grace period), ARQ-воркер `data_deletion_processor` (cron 03:00 UTC, hard-delete по истечении 30 дней с CASCADE), интеграционные тесты сервисного слоя против реального Postgres (4 кейса в `tests/integration/`), CI расширен на интеграционные тесты.
- **Локальный стек проверен и работает** (2026-05-10): Docker Desktop установлен, `docker compose up -d` поднимает все 5 сервисов, миграция применена, онбординг FSM пройден до конца в Telegram.
- Спринт 3 — модуль питания: модели `food_items` / `food_aliases` / `food_logs` (partitioned by month, append-only через PL/pgSQL trigger, snapshot нутриентов), миграция с `pg_trgm` extension и GIN trgm-индексами для fuzzy-поиска на 4 языках; сидинг `manual_foods` (топ-30 базовых продуктов с RU/EN/PL/DE алиасами), USDA FoodData Central API loader (опционально, требует USDA_FDC_API_KEY), Open Food Facts API loader для брендовых продуктов; `ClaudeClient.call_text` с prompt caching (cache_control: ephemeral) и retry на 429/5xx; nutrition parser (Haiku 4.5) с системным промптом `<json>...</json>`-формата; `Orchestrator` с детерминированным regex-классификатором (число+единица → 0.95, leading number → 0.92, глагол → 0.7); bot handler `/log` с FSM `choosing_match` и inline-кнопками выбора кандидата; интеграционный тест-suite через alembic upgrade (а не create_all) — 9 кейсов на pg_trgm fuzzy, snapshot нутриентов, partition routing, immutability trigger, daily_totals.
- Спринт 4 — Vision Phase 1: модель `photo_recognitions` (pHash, items_json, photo_kept=false — GDPR); миграция `20260510_1600`; `ClaudeClient.call_vision` (base64 image, Sonnet 4.6, cache_system, retry); системный промпт `src/agents/prompts/vision_phase1.md` (multilingual, weight estimation rules, chain brand detection, `<json>...</json>` output); `VisionParser.recognize` с pHash-кэшем (точное совпадение → быстрый SQL, приближённое ≤5 Хэмминг → Python-цикл по last 100); `VisionStates.confirming_item` + `entering_grams` FSM; `src/bot/handlers/vision.py` с очередью распознанных продуктов → подтверждение / ввод граммов / пропуск → NutritionService.search → log_food(method=PHOTO_PHASE1); 15 unit-тестов + 4 интеграционных (3 passed, 1 skipped). Итого: **71 passed, 1 skipped**.

**Следующий шаг:** Спринт 5 — Vision Phase 2 (chain DB + visual weight range), кнопки ±10г, daily check-in, Recovery Index.

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
| 2026-05-10 | Полный i18n-проход (`_()` обёртка handler-строк) **отложен** до подключения переводчиков PL/DE (спринт 6+). До этого RU = master, английский остаётся хардкодом. `.po` создаются при первом проходе через `make i18n-extract`. | Преждевременная локализация — anti-pattern, нужны живые переводчики |
| 2026-05-10 | Hard-delete пользователей — через CASCADE на FK (ON DELETE CASCADE стоит на user_profiles, consent_records и т.д.). ARQ-воркер делает `DELETE FROM users WHERE id IN (...)`. | Один источник правды (БД), нет ручной разборки таблиц в коде |
| 2026-05-10 | Grace period конфигурируется через `GDPR_DELETION_GRACE_DAYS` в .env (по умолчанию 30). Для тестирования ставится 0. | гибкость для CI / staging |
| 2026-05-10 | Интеграционные тесты идут через реальный Postgres (CI service container или локальный `make dev` БД). aiosqlite-fallback не используется — модели завязаны на postgres-специфику (UUID, ENUM, ARRAY). | Faithful tests > быстрые in-memory |
| 2026-05-10 | `food_logs` — partitioned by RANGE (logged_at), 12 месячных партиций на 2026 + DEFAULT. Партиции 2027+ создаст ARQ-воркер ближе к делу. | Без партиционирования food_logs за год вахтовика разрастётся в десятки тысяч строк; партиции дают дешёвый retention drop по году |
| 2026-05-10 | Immutability `food_logs` через PL/pgSQL trigger (`RAISE EXCEPTION` на UPDATE), не через REVOKE. DELETE разрешён для GDPR Art. 17 каскада. | Не зависит от роли БД, работает в dev и prod одинаково |
| 2026-05-10 | Snapshot нутриентов в `food_logs.kcal/protein_g/...` на момент логирования. Изменения в `food_items` не переписывают историю. | Требование ТЗ §5: immutable health data + audit trail |
| 2026-05-10 | Fuzzy-поиск через `pg_trgm` GIN-индексы на `lower(alias)` + мультиязычные `food_aliases` per-locale. Tsvector / морфологические словари не используем. | trgm устойчив к опечаткам и работает на 4 языках без словарей; кириллица + латиница из коробки |
| 2026-05-10 | Базовый каталог из 30 продуктов (`scripts/lib/manual_foods.py`) с алиасами на RU/EN/PL/DE — обязательное основание. USDA + OFF подключаются как «расширение». | Без manual seed русский текст-ввод не сработает: USDA только en, OFF преимущественно бренды |
| 2026-05-10 | Prompt caching обязателен на каждом системном промпте (`cache_control: ephemeral`). На Haiku 4.5 даёт ~10× экономию по cache_read токенам внутри 5-мин TTL. | CLAUDE.md §2.1 — фиксированное правило проекта |
| 2026-05-10 | Nutrition parser — text-only Haiku вызов с `<json>...</json>`-блоком ответа. Структурный JSON не через tool_use. | Tool_use дороже (больше токенов на schema) и сложнее отлаживать; tag-based парсинг достаточен и устойчив |
| 2026-05-10 | Censor НЕ применяется к Orchestrator и nutrition_parser. Censor — только на Coach/RAG ответах. | CLAUDE.md §3.2: nutrition-парсинг не health-advice; защита Censor не нужна на детерминированных задачах |
| 2026-05-10 | Auto-log threshold = `similarity >= 0.85`. Иначе показываем top-3 inline-кнопок. | Эмпирический порог: точные совпадения «куриная грудка»/«грудка курицы» дают ≥0.62, «помидоры» с опечаткой даёт ~0.5; 0.85 минимизирует ложные авто-логи |
| 2026-05-10 | Интеграционные тесты используют **alembic upgrade head** (subprocess), не `Base.metadata.create_all`. | Без миграций нет partitioned table, pg_trgm extension, и PL/pgSQL trigger |
| 2026-05-10 | Фото НЕ хранится — только `phash` (16-hex, 64-bit imagehash) + `items_json` в `photo_recognitions`. `photo_kept = false` всегда. | GDPR Art. 5(1)(c) Data Minimisation — хранить само фото еды нет правового основания |
| 2026-05-10 | Vision output: `<json>...</json>` тег как в nutrition parser, не tool_use. | Tool_use дороже по токенам + не нужен для структурированного JSON с 5–6 полями |
| 2026-05-10 | pHash cache: точное совпадение → SQL lookup; ≤5 Хэмминг → Python-цикл по last 100 записям за 30 дней. | Без pg extension для bit-distance точный lookup бесплатен; 100 записей пользователя за 30 дней — реалистичный максимум |
| 2026-05-10 | Vision log threshold = `similarity >= 0.5` (мягче 0.85 текстового). | Vision уже нормализует name_ru через Sonnet; нет смысла поднимать планку — лучше логировать «приближённо» и дать пользователю исправить |

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
- **2026-05-10 — спринт 2.** Полный i18n-проход откладывается, см. таблицу решений. RU остаётся master-языком до подключения переводчиков. `LOCALE_LABELS` уже умеют все 4 языка, переключение в `/settings` сохраняется в БД, но влияет только на новые `_()`-обёрнутые сообщения (которые появятся в спринтах 6+).
- **2026-05-10 — спринт 2.** Тестовая БД для интеграционных тестов = `bioarchitect_test`. CI создаёт её через service container с такими же кредами как dev. Локально нужно создать вручную: `docker compose exec postgres createdb -U bioarchitect bioarchitect_test`.
- **2026-05-10 — локальный запуск.** Исправлены баги при первом запуске: (1) `SUPPORTED_LOCALES` в `.env` должен быть в JSON-формате `["ru","en","pl","de"]`; (2) `structlog.stdlib.add_logger_name` убран из процессоров (несовместим с `PrintLoggerFactory`); (3) все `DateTime()` колонки переведены на `DateTime(timezone=True)` — иначе asyncpg падал с "can't subtract offset-naive and offset-aware datetimes"; (4) `alembic.ini` добавлен в volumes бота в `docker-compose.yml`; (5) `README.md` добавлен в Dockerfile `dev` и `builder` стадии (hatchling требует его при сборке пакета).
- **2026-05-10 — спринт 3.** Тестовая БД `bioarchitect_test` теперь поднимается через **alembic upgrade head** (subprocess) на `tests/integration/conftest.py`, а не через `Base.metadata.create_all`. Без этого partitioned `food_logs`, pg_trgm extension и PL/pgSQL trigger не разворачиваются. Per-test изоляция — через `TRUNCATE ... CASCADE` после каждого теста. Engine — function-scoped (session-scoped не работает с `asyncio_mode = "auto"` из pytest-asyncio 0.24+: разные тесты получают разные event loop'ы → `Event loop is closed` при close).
- **2026-05-10 — спринт 3.** OFF API возвращает много мусорных записей (французские названия без RU/PL/DE-алиасов, `Fromage de France`-подобные). Поставили `verified=false` на всё что из OFF, чтобы не использовать в auto-log path (нужен `verified=true`). В спринте 4 добавим фильтр по длине алиаса и наличию минимального набора нутриентов.
- **2026-05-10 — спринт 3.** Pending entries в FSM-state (выбор кандидата по кнопкам) сериализуются как dict с UUID-as-str. Если Redis-storage перезагрузится между сообщениями — state потеряется. Для MVP ок (Redis с appendonly=yes), при росте — переехать на DB-backed FSM.

## 5. Текущий план спринтов

| Спринт | Недели | Цель | Статус |
|---|---|---|---|
| 0 | — | Скаффолдинг репозитория | ✅ done |
| 1 | 1–2 | Docker Compose, Postgres, Alembic, FSM-онбординг 8 шагов (GDPR + 5 этапов), таблицы users/profiles/consents | ✅ done |
| 2 | 3–4 | главное меню, `/profile`, `/settings`, soft-delete + ARQ hard-delete воркер, integration tests | ✅ done |
| 3 | 5–6 | Сидинг USDA + Open Food Facts, ручной ввод (Haiku 4.5) через Orchestrator, pg_trgm fuzzy search | ✅ done |
| 4 | 7–8 | Vision Phase 1 (распознавание + редактирование), pHash-кэш | ✅ done |
| 5 | 9–10 | Vision Phase 2 (chain DB + visual range), кнопки ±10г, daily check-in, Recovery Index | ⏭️ next |
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
