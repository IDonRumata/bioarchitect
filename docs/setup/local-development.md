# Локальная разработка — пошаговая инструкция для Андрея

> Целевая среда: **Windows 11 + Docker Desktop + Git Bash + VS Code**.
> Для macOS / Linux команды совпадают.

## Шаг 1. Установить инструменты

```powershell
# Docker Desktop — обязательно
winget install Docker.DockerDesktop

# uv — быстрый менеджер зависимостей Python
winget install astral-sh.uv

# GitHub CLI (опционально, удобно для PR)
winget install GitHub.cli
```

После установки Docker Desktop:
1. Запусти его.
2. Дождись, пока в трее появится "Docker is running".
3. В Settings → Resources → выдели **минимум 4 GB RAM**.

## Шаг 2. Клонировать репозиторий

```bash
cd "D:/Claude Code doc/Projects"
git clone https://github.com/IDonRumata/bioarchitect.git
cd bioarchitect
```

## Шаг 3. Настроить `.env`

```bash
cp .env.example .env
```

Открой `.env` в редакторе и заполни:

| Переменная | Где взять |
|---|---|
| `TELEGRAM_BOT_TOKEN` | у @BotFather: `/newbot` |
| `TELEGRAM_BOT_USERNAME` | имя бота без @ |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `POSTGRES_PASSWORD` | придумай локально, любую строку |

Остальные переменные оставь пустыми — они нужны на более поздних спринтах.

## Шаг 4. Запустить локальный стек

```bash
make dev
```

Эта команда:
1. Скачивает Postgres + Redis в Docker.
2. Собирает Docker-образ бэкенда.
3. Запускает 4 сервиса: postgres, redis, bot, api, worker.

В логах увидишь `bot.started username=<твой_бот>`.

## Шаг 5. Проверить, что всё работает

В Telegram открой своего бота → `/start`. Должно прийти приветствие
"Это BioArchitect — твой AI-помощник…".

API health check:
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Шаг 6. Применить миграции БД (после спринта 1)

```bash
make migrate
```

## Если что-то сломалось

```bash
make logs               # хвост логов всех сервисов
make dev-down           # остановить
make dev-clean          # остановить и удалить тома (данные потеряются!)
```

Если совсем плохо:
```bash
docker system prune -af  # снести всё Docker и собрать заново
make dev
```

## Полезные команды

```bash
make test               # запустить тесты
make lint               # ruff + mypy
make format             # автоформат
make migrate-new m="add_users_table"   # создать миграцию
make eval               # eval suite Censor (CI gate)
```
