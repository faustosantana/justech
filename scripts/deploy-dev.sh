#!/usr/bin/env bash
# Deploy DEV — sincroniza addons desde Git y reinicia stack
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="$PROJECT_ROOT/repository"
COMPOSE_DIR="$PROJECT_ROOT/docker/dev"
ENV_FILE="$PROJECT_ROOT/config/dev/.env"
COMMIT="${1:-develop}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/deploy-dev-$(date +%Y-%m-%d_%H%M).log"

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

rsync -av --delete "$REPO/custom/" "$PROJECT_ROOT/custom/"

if [[ ! -f "$ENV_FILE" ]]; then
  log "ERROR: Crear $ENV_FILE desde .env.example antes de desplegar"
  exit 1
fi

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" up -d

log "DEV desplegado — commit: $(git -C "$REPO" rev-parse --short HEAD)" | tee -a "$LOG_FILE"
log "URL: https://dev.hellenia.cloud" | tee -a "$LOG_FILE"
