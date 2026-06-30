#!/usr/bin/env bash
# Deploy TEST — sincroniza addons desde Git (rama test) y reinicia stack
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="$PROJECT_ROOT/repository"
COMPOSE_DIR="$PROJECT_ROOT/docker/test"
ENV_FILE="$PROJECT_ROOT/config/test/.env"
COMMIT="${1:-test}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/deploy-test-$(date +%Y-%m-%d_%H%M).log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

mkdir -p "$(dirname "$LOG_FILE")"

if [[ ! -d "$REPO/.git" ]]; then
  log "ERROR: Repositorio Git no inicializado en $REPO"
  exit 1
fi

cd "$REPO"
git fetch origin 2>/dev/null || true
git checkout "$COMMIT"
git pull origin "$COMMIT" 2>/dev/null || true

rsync -av --delete "$REPO/addons/" "$PROJECT_ROOT/addons/"

if [[ ! -f "$ENV_FILE" ]]; then
  log "ERROR: Crear $ENV_FILE desde .env.example antes de desplegar"
  exit 1
fi

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" up -d

log "TEST desplegado — commit: $(git -C "$REPO" rev-parse --short HEAD)" | tee -a "$LOG_FILE"
log "URL: https://test.hellenia.cloud" | tee -a "$LOG_FILE"
