#!/usr/bin/env bash
# CRM Tuyen Sinh - restore Postgres tu file backup pg_backup.sh tao ra
#
# Cach goi:
#   bash /var/www/thanhdat/infra/scripts/pg_restore.sh /var/backups/thanhdat/crm-YYYYMMDD-HHMM.sql.gz
#   bash /var/www/thanhdat/infra/scripts/pg_restore.sh --latest
#
# CANH BAO: Script DROP + RECREATE database. Toan bo du lieu hien tai bi mat.
# Phai stop backend + celery truoc khi chay (de tranh write conflict trong khi restore).
#
# Env optional (cung ten voi pg_backup.sh):
#   BACKUP_DIR             /var/backups/thanhdat
#   COMPOSE_PROJECT_DIR    /var/www/thanhdat/infra
#   COMPOSE_ENV_FILE       .env.prod
#   DB_CONTAINER           thanhdat-db

set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/thanhdat}"
COMPOSE_PROJECT_DIR="${COMPOSE_PROJECT_DIR:-/var/www/thanhdat/infra}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.env.prod}"
DB_CONTAINER="${DB_CONTAINER:-thanhdat-db}"

if [[ $# -lt 1 ]]; then
  cat >&2 <<'EOF'
Usage: pg_restore.sh <path-to-backup.sql.gz>
       pg_restore.sh --latest

CANH BAO: Script DROP database. Toan bo du lieu hien tai bi mat.
EOF
  exit 1
fi

# Resolve backup file.
if [[ "$1" == "--latest" ]]; then
  BACKUP_FILE=$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'crm-*.sql.gz' \
    -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | head -n1 | cut -d' ' -f2-)
  if [[ -z "$BACKUP_FILE" ]]; then
    echo "ERROR: Khong tim thay backup nao trong $BACKUP_DIR." >&2
    exit 1
  fi
  echo "Restore tu backup moi nhat: $BACKUP_FILE"
else
  BACKUP_FILE="$1"
fi

if [[ ! -r "$BACKUP_FILE" ]]; then
  echo "ERROR: Khong doc duoc file $BACKUP_FILE." >&2
  exit 1
fi

if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
  echo "ERROR: File gzip corrupt: $BACKUP_FILE." >&2
  exit 1
fi

# Doc env.
ENV_PATH="$COMPOSE_PROJECT_DIR/$COMPOSE_ENV_FILE"
if [[ ! -r "$ENV_PATH" ]]; then
  echo "ERROR: Khong doc duoc env file $ENV_PATH." >&2
  exit 1
fi
# shellcheck disable=SC1090
set -a
. "$ENV_PATH"
set +a

if [[ -z "${POSTGRES_USER:-}" || -z "${POSTGRES_DB:-}" ]]; then
  echo "ERROR: POSTGRES_USER hoac POSTGRES_DB rong trong $ENV_PATH." >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
  echo "ERROR: Container $DB_CONTAINER khong chay." >&2
  exit 1
fi

# Xac nhan thu cong (interactive). Cron tuyet doi khong duoc goi script nay.
echo ""
echo "=========================================="
echo "  RESTORE POSTGRES TU BACKUP"
echo "=========================================="
echo "  File:     $BACKUP_FILE"
echo "  Database: $POSTGRES_DB"
echo "  User:     $POSTGRES_USER"
echo "  Container:$DB_CONTAINER"
echo "------------------------------------------"
echo "  Database $POSTGRES_DB se bi DROP + tao lai."
echo "  Toan bo du lieu hien tai SE MAT."
echo "=========================================="
read -r -p "Go RESTORE de xac nhan: " ANSWER
if [[ "$ANSWER" != "RESTORE" ]]; then
  echo "Huy bo."
  exit 0
fi

echo "Drop + recreate database..."
docker exec -i "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d postgres <<SQL
SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$POSTGRES_DB";
CREATE DATABASE "$POSTGRES_DB" OWNER "$POSTGRES_USER";
SQL

echo "Restore du lieu tu $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" --quiet

echo "Restore xong."
echo "Nho start lai backend + celery: docker compose up -d"
