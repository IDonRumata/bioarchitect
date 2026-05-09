#!/usr/bin/env bash
# BioArchitect — ежедневный pg_dump → Backblaze B2 EU
# Запуск через cron на VPS: 0 3 * * * /opt/bioarchitect/infra/backup/pg_backup.sh
#
# Реализация — спринт 7.
# Заглушка для понимания структуры.

set -euo pipefail

DATE="$(date -u +%Y-%m-%d_%H-%M-%S)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/bioarchitect}"
B2_BUCKET="${B2_BUCKET:-bioarchitect-backups-eu}"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"
DUMP_FILE="${BACKUP_DIR}/bioarchitect_${DATE}.sql.gz"

echo "[backup] starting pg_dump → ${DUMP_FILE}"

docker compose exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-bioarchitect}" \
    -d "${POSTGRES_DB:-bioarchitect}" \
    --format=custom \
    --no-owner \
    --no-privileges \
    | gzip > "${DUMP_FILE}"

echo "[backup] uploading to B2..."
b2 upload-file "${B2_BUCKET}" "${DUMP_FILE}" "daily/$(basename "${DUMP_FILE}")"

echo "[backup] pruning local backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -mtime "+${RETENTION_DAYS}" -delete

echo "[backup] done."
