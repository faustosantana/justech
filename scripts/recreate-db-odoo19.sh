#!/usr/bin/env bash
# Recrea BD Odoo 19 desde cero (hellenia_dev / hellenia_test)
# Uso cuando la BD proviene de Odoo 18 y el upgrade in-place falla.
# Uso: recreate-db-odoo19.sh dev|test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET="${1:-}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

usage() {
  echo "Uso: $0 dev|test"
  exit 1
}

[[ "$TARGET" == "dev" || "$TARGET" == "test" ]] || usage

COMPOSE_DIR="$PROJECT_ROOT/docker/${TARGET}"
ENV_FILE="$PROJECT_ROOT/config/${TARGET}/.env"
DB_CONTAINER="hellenia-${TARGET}-db-1"
DB_NAME="hellenia_${TARGET}"

# shellcheck disable=SC1090
source "$ENV_FILE"

log "=== Recrear BD $DB_NAME en Odoo 19 ==="

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" stop odoo

docker exec "$DB_CONTAINER" psql -U "${DB_USER:-odoo}" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" \
  2>/dev/null || true

docker exec "$DB_CONTAINER" psql -U "${DB_USER:-odoo}" -d postgres -c "DROP DATABASE IF EXISTS \"${DB_NAME}\";"
docker exec "$DB_CONTAINER" psql -U "${DB_USER:-odoo}" -d postgres -c \
  "CREATE DATABASE \"${DB_NAME}\" OWNER \"${DB_USER:-odoo}\";"

docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
  -d "$DB_NAME" --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
  -i base --stop-after-init --without-demo=all

docker compose --env-file "$ENV_FILE" up -d odoo
log "BD $DB_NAME recreada. Validar con: validate-odoo19.sh $TARGET"
