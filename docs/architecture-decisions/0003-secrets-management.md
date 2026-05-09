# ADR-0003: Secrets management — sops + age

- **Дата:** 2026-05-09
- **Статус:** accepted
- **Авторы:** Андрей, Claude

## Контекст

Нужен способ хранить API-ключи (Anthropic, Telegram, Stripe, Backblaze, ЮKassa)
в репозитории безопасно. ТЗ упоминает Doppler ИЛИ sops/age. Doppler — SaaS
($0 free tier, но ограничен и не EU-friendly).

## Решение

**sops + age:**
- Шифрованные `.env`-файлы (`.env.encrypted`) хранятся в git.
- Ключ дешифровки (`age` private key) — только у владельца локально и в
  GitHub Actions secrets.
- Audit trail — встроен в git (кто менял зашифрованный файл и когда).

## Альтернативы

1. **Doppler** — отвергнуто:
   - Free tier ограничен 5 проектами / 3 пользователями, без audit log.
   - SaaS-зависимость на критическом пути запуска приложения.
   - Серверы в US, не идеально для GDPR-проекта.
2. **AWS Secrets Manager / GCP Secret Manager** — отвергнуто: лишняя зависимость
   на cloud-провайдера, у нас Hetzner / Zomro / Beget.
3. **HashiCorp Vault** — отвергнуто: оверхед для одного разработчика.
4. **`.env` в git** — отвергнуто, очевидно небезопасно.

## Последствия

**Плюсы:**
- Бесплатно.
- Audit trail в git.
- Деплой — один шаг: `sops -d .env.encrypted > .env` на VPS.
- Работает в CI: `age` ключ как GitHub Actions secret.

**Минусы:**
- Андрею нужно установить sops и age локально (одна команда: `winget install sops age`).
- Ротация ключей — ручная (раз в 6 мес).
- Если ключ age потерян — все секреты теряются. Бэкап ключа в менеджере паролей
  обязателен.

## Реализация

- Каталог `secrets/` в .gitignore.
- Файл `.sops.yaml` в корне с правилами шифрования.
- Команды в Makefile: `make secrets-encrypt`, `make secrets-decrypt`.
- Отдельная инструкция для Андрея в `docs/setup/secrets.md` (TODO sprint 1).
