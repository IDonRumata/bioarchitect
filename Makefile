# BioArchitect — главный Makefile

.DEFAULT_GOAL := help
SHELL := /bin/bash

# Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m

.PHONY: help
help:  ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ---------- Локальная разработка ----------

.PHONY: dev
dev:  ## Запустить весь стек локально (postgres + redis + bot + api)
	docker compose up --build

.PHONY: dev-detach
dev-detach:  ## То же, но в фоне
	docker compose up -d --build

.PHONY: dev-down
dev-down:  ## Остановить локальный стек
	docker compose down

.PHONY: dev-clean
dev-clean:  ## Остановить и удалить тома (данные теряются!)
	docker compose down -v

.PHONY: logs
logs:  ## Хвост логов всех сервисов
	docker compose logs -f --tail=100

.PHONY: shell-bot
shell-bot:  ## Зайти в контейнер бота
	docker compose exec bot /bin/bash

.PHONY: shell-db
shell-db:  ## Зайти в psql
	docker compose exec postgres psql -U bioarchitect -d bioarchitect

# ---------- Установка ----------

.PHONY: install
install:  ## Установить Python-зависимости через uv
	uv sync --all-extras

.PHONY: install-prod
install-prod:  ## Только продакшн-зависимости
	uv sync

# ---------- Качество кода ----------

.PHONY: lint
lint:  ## ruff check + mypy --strict
	uv run ruff check src tests
	uv run mypy src

.PHONY: format
format:  ## ruff format + ruff fix
	uv run ruff format src tests
	uv run ruff check --fix src tests

.PHONY: typecheck
typecheck:  ## Только mypy
	uv run mypy src

# ---------- Тесты ----------

.PHONY: test
test:  ## Все тесты
	uv run pytest

.PHONY: test-unit
test-unit:  ## Только unit-тесты
	uv run pytest -m unit

.PHONY: test-integration
test-integration:  ## Integration-тесты (нужен Docker)
	uv run pytest -m integration

.PHONY: test-cov
test-cov:  ## Тесты с coverage report
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

.PHONY: eval
eval:  ## Eval suite Censor Agent (CI gate, должен пройти 100%)
	uv run pytest -m censor_eval --tb=short
	@echo "$(GREEN)✓ Censor Agent eval passed$(NC)"

# ---------- Миграции БД ----------

.PHONY: migrate
migrate:  ## Применить все миграции
	uv run alembic upgrade head

.PHONY: migrate-down
migrate-down:  ## Откатить последнюю миграцию
	uv run alembic downgrade -1

.PHONY: migrate-new
migrate-new:  ## Создать новую миграцию: make migrate-new m="add_users_table"
	@if [ -z "$(m)" ]; then echo "$(RED)Usage: make migrate-new m=\"description\"$(NC)"; exit 1; fi
	uv run alembic revision --autogenerate -m "$(m)"

.PHONY: migrate-history
migrate-history:  ## Показать историю миграций
	uv run alembic history

# ---------- Сидинг данных ----------

.PHONY: seed
seed:  ## Засеять все справочники (food_items, lab_markers, lab_reference_ranges)
	uv run python -m scripts.seed_all

.PHONY: seed-food
seed-food:  ## Только USDA + Open Food Facts
	uv run python -m scripts.seed_food_items

.PHONY: seed-chains
seed-chains:  ## Только база заправок и фастфуда (через PDF-парсер)
	uv run python -m scripts.seed_chain_menus

.PHONY: seed-labs
seed-labs:  ## Только маркеры и референсы (требует подписи медэдвайзера)
	uv run python -m scripts.seed_lab_markers

# ---------- Локализация ----------

.PHONY: i18n-extract
i18n-extract:  ## Извлечь строки в .pot
	uv run pybabel extract -F babel.cfg -o locale/messages.pot src/

.PHONY: i18n-update
i18n-update:  ## Обновить .po-файлы из .pot
	uv run pybabel update -i locale/messages.pot -d locale -l ru
	uv run pybabel update -i locale/messages.pot -d locale -l en
	uv run pybabel update -i locale/messages.pot -d locale -l pl
	uv run pybabel update -i locale/messages.pot -d locale -l de

.PHONY: i18n-compile
i18n-compile:  ## Скомпилировать .po → .mo
	uv run pybabel compile -d locale

# ---------- Деплой (заглушки до спринта 7) ----------

.PHONY: deploy-staging
deploy-staging:  ## Деплой на staging-VPS
	@echo "$(YELLOW)TODO: реализовать в спринте 7$(NC)"

.PHONY: deploy-prod
deploy-prod:  ## Деплой в продакшн (только из main, после CI)
	@echo "$(YELLOW)TODO: реализовать в спринте 7$(NC)"

# ---------- Безопасность ----------

.PHONY: security-scan
security-scan:  ## Сканер уязвимостей
	uv run pip-audit || true

.PHONY: secrets-check
secrets-check:  ## Проверить, не утекли ли секреты в git
	gitleaks detect --source . --no-banner

# ---------- Очистка ----------

.PHONY: clean
clean:  ## Удалить кэши Python
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage coverage.xml dist build *.egg-info
