#!/usr/bin/env bash
# Deploy TEST — sincroniza infra + custom desde Git y reinicia stack
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMMIT="${1:-hellenia-odoo-infra}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/deploy-test-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$LOG_FILE")"

if [[ ! -d "$REPO/.git" ]]; then
  hellenia_log "ERROR: Repositorio Git no encontrado en $REPO"
  exit 1
fi

cd "$REPO"
git fetch origin 2>/dev/null || true
git checkout "$COMMIT"
git pull origin "$COMMIT" 2>/dev/null || true

hellenia_sync_from_repo "$REPO" "$PROJECT_ROOT"
hellenia_load_env "$ENV_FILE"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" pull odoo db 2>/dev/null || true
docker compose --env-file "$ENV_FILE" up -d

hellenia_log "TEST desplegado — commit: $(git -C "$REPO" rev-parse --short HEAD)" | tee -a "$LOG_FILE"
hellenia_log "URL: https://test.hellenia.cloud" | tee -a "$LOG_FILE"
