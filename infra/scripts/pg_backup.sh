#!/usr/bin/env bash
# CRM Tuyen Sinh - pg_dump backup daily
#
# Dump database Postgres trong container thanhdat-db, gzip, dat vao
# /var/backups/thanhdat/. Rotate giu 30 ngay theo retention quy dinh
# o acceptance criteria Sprint 3 (docs/03-phase1-plan.md:312).
#
# Cach goi:
#   bash /var/www/thanhdat/infra/scripts/pg_backup.sh          # backup daily
#   bash /var/www/thanhdat/infra/scripts/pg_backup.sh --check  # health check, khong dump
#
# Cron: /etc/cron.d/thanhdat-pg-backup (xem infra/cron/).
#
# Env optional (de set trong /etc/default/thanhdat-backup neu can):
#   BACKUP_DIR             /var/backups/thanhdat
#   BACKUP_RETENTION_DAYS  30
#   BACKUP_LOG             /var/log/thanhdat-backup.log
#   COMPOSE_PROJECT_DIR    /var/www/thanhdat/infra
#   COMPOSE_ENV_FILE       .env.prod
#   COMPOSE_FILE           docker-compose.prod.yml
#   DB_CONTAINER           thanhdat-db
#   BACKUP_S3_BUCKET       <unset>   # neu set, sync len R2/S3 sau khi dump (phase 2)

set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/thanhdat}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_LOG="${BACKUP_LOG:-/var/log/thanhdat-backup.log}"
COMPOSE_PROJECT_DIR="${COMPOSE_PROJECT_DIR:-/var/www/thanhdat/infra}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DB_CONTAINER="${DB_CONTAINER:-thanhdat-db}"
BACKUP_S3_BUCKET="${BACKUP_S3_BUCKET:-}"

# Log helper: stdout + file. Cron mailer chi nhan stderr neu fail.
log() {
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  printf '[%s] %s\n' "$ts" "$*" | tee -a "$BACKUP_LOG"
}

err() {
  local ts
  ts="$(date '+%Y-%m-%d %H:%M:%S')"
  printf '[%s] ERROR: %s\n' "$ts" "$*" | tee -a "$BACKUP_LOG" >&2
}

# Trap loi de log truoc khi exit, cron se thay exit code != 0.
on_error() {
  err "Backup that bai o dong $1. Xem chi tiet trong $BACKUP_LOG."
  exit 1
}
trap 'on_error $LINENO' ERR

# Health check mode: kiem tra container song + thu muc write duoc.
if [[ "${1:-}" == "--check" ]]; then
  log "Health check: BACKUP_DIR=$BACKUP_DIR DB_CONTAINER=$DB_CONTAINER"
  if ! docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    err "Container $DB_CONTAINER khong chay."
    exit 2
  fi
  mkdir -p "$BACKUP_DIR"
  touch "$BACKUP_DIR/.write-test"
  rm -f "$BACKUP_DIR/.write-test"
  log "Health check OK."
  exit 0
fi

# Doc POSTGRES_USER + POSTGRES_DB tu .env.prod (KHONG hardcode).
ENV_PATH="$COMPOSE_PROJECT_DIR/$COMPOSE_ENV_FILE"
if [[ ! -r "$ENV_PATH" ]]; then
  err "Khong doc duoc env file $ENV_PATH."
  exit 1
fi

# shellcheck disable=SC1090
set -a
. "$ENV_PATH"
set +a

if [[ -z "${POSTGRES_USER:-}" || -z "${POSTGRES_DB:-}" ]]; then
  err "POSTGRES_USER hoac POSTGRES_DB rong trong $ENV_PATH."
  exit 1
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

STAMP="$(date '+%Y%m%d-%H%M')"
OUT_FILE="$BACKUP_DIR/crm-${STAMP}.sql.gz"
TMP_FILE="${OUT_FILE}.partial"

log "Bat dau dump: db=$POSTGRES_DB user=$POSTGRES_USER container=$DB_CONTAINER -> $OUT_FILE"

# Dump qua docker exec, KHONG ghi temp ra host vi giam I/O + bao mat.
# --no-owner --no-privileges de restore qua user khac duoc.
if ! docker exec -i "$DB_CONTAINER" \
    pg_dump --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    | gzip -c > "$TMP_FILE"; then
  rm -f "$TMP_FILE"
  err "pg_dump that bai. File partial da xoa."
  exit 1
fi

# Atomic rename.
mv "$TMP_FILE" "$OUT_FILE"
chmod 600 "$OUT_FILE"

SIZE_BYTES=$(stat -c '%s' "$OUT_FILE" 2>/dev/null || stat -f '%z' "$OUT_FILE")
SIZE_HUMAN=$(numfmt --to=iec --suffix=B "$SIZE_BYTES" 2>/dev/null || echo "${SIZE_BYTES}B")
log "Dump xong: $OUT_FILE ($SIZE_HUMAN)."

# Sanity check: file gzip phai valid + size > 1KB (DB rong cung > 1KB header).
if ! gzip -t "$OUT_FILE" 2>/dev/null; then
  err "File gzip corrupt: $OUT_FILE."
  exit 1
fi
if [[ "$SIZE_BYTES" -lt 1024 ]]; then
  err "File size $SIZE_BYTES byte < 1KB - dump co the rong."
  exit 1
fi

# Rotate: xoa file > N ngay.
DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'crm-*.sql.gz' \
  -mtime "+$BACKUP_RETENTION_DAYS" -print -delete | wc -l)
if [[ "$DELETED" -gt 0 ]]; then
  log "Da xoa $DELETED file backup > $BACKUP_RETENTION_DAYS ngay."
fi

# Phase 2: sync len S3/R2 neu set BACKUP_S3_BUCKET.
if [[ -n "$BACKUP_S3_BUCKET" ]]; then
  if command -v aws >/dev/null 2>&1; then
    log "Sync len S3: s3://$BACKUP_S3_BUCKET/$(basename "$OUT_FILE")"
    aws s3 cp "$OUT_FILE" "s3://$BACKUP_S3_BUCKET/" --only-show-errors \
      && log "Sync S3 xong." \
      || err "Sync S3 that bai (giu local backup)."
  else
    err "BACKUP_S3_BUCKET set nhung aws CLI khong co - bo qua sync."
  fi
fi

log "Backup hoan tat."
exit 0
