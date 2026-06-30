#!/usr/bin/env bash
# Promoción controlada a producción — flujo obligatorio Fase 13.7+
#
# DEV → TEST → CERTIFICACIÓN → BACKUP PROD → PROMOCIÓN → HEALTHCHECK → SMOKE → GO-LIVE
#
# Uso:
#   CERTIFIED_COMMIT=<sha> APPROVE_PROMOTION=1 ./promote-to-production.sh
#
# NO modifica PROD sin APPROVE_PROMOTION=1 y evidencia TEST PASS.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
CERTIFIED_COMMIT="${CERTIFIED_COMMIT:-}"
EVIDENCE_FILE="${EVIDENCE_FILE:-$PROJECT_ROOT/evidence/phase14-final-acceptance.json}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/promote-prod-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$LOG_FILE")"

log() { hellenia_log "$*" | tee -a "$LOG_FILE"; }

abort() {
  log "ABORT PROMOCIÓN: $*"
  log "DETENER — no continuar."
  exit 1
}

log "=== Promoción a producción (pipeline certificado) ==="

# --- Gate 1: Aprobación explícita ---
if [[ "${APPROVE_PROMOTION:-}" != "1" ]]; then
  abort "Falta APPROVE_PROMOTION=1 (aprobación explícita requerida)"
fi

# --- Gate 2: Commit certificado ---
if [[ -z "$CERTIFIED_COMMIT" ]]; then
  abort "Falta CERTIFIED_COMMIT (commit validado en TEST)"
fi

# --- Gate 3: Evidencia TEST PASS ---
if [[ ! -f "$EVIDENCE_FILE" ]]; then
  abort "Sin evidencia TEST: $EVIDENCE_FILE"
fi
if ! python3 -c "
import json, sys
d=json.load(open('$EVIDENCE_FILE'))
sys.exit(0 if d.get('ok') else 1)
" 2>/dev/null; then
  abort "Evidencia TEST no es PASS: $EVIDENCE_FILE"
fi
log "OK  Evidencia TEST PASS: $EVIDENCE_FILE"

# --- Gate 4: Healthcheck TEST previo ---
log "Ejecutando healthcheck TEST antes de promoción..."
if ! "$SCRIPT_DIR/healthcheck-full.sh" test 2>&1 | tee -a "$LOG_FILE"; then
  abort "Healthcheck TEST falló — no promover a PROD"
fi

# --- Gate 5: Sincronizar repo al commit certificado ---
if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  git fetch origin 2>/dev/null || true
  git checkout "$CERTIFIED_COMMIT" || abort "Commit $CERTIFIED_COMMIT no encontrado"
  hellenia_sync_from_repo "$REPO" "$PROJECT_ROOT"
  log "OK  Repo en commit $(git rev-parse --short HEAD)"
else
  log "WARN: Sin repo Git — usando artefactos locales"
fi

# --- Gate 6: Backup PROD (obligatorio) ---
log "Backup producción (obligatorio antes de promoción)..."
if ! "$SCRIPT_DIR/backup-hellenia-prod.sh" 2>&1 | tee -a "$LOG_FILE"; then
  abort "Backup PROD falló"
fi
BACKUP_DIR=$(ls -1dt "${BACKUP_ROOT:-$PROJECT_ROOT/backups/hellenia-prod}"/20* 2>/dev/null | head -1)
log "OK  Backup: $BACKUP_DIR"

# --- Promoción: solo infra (docker compose) — sin instalar módulos ---
hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"
log "Aplicando docker-compose certificado (force-recreate odoo)..."
docker compose --env-file "$ENV_FILE" config >/dev/null || abort "docker compose config inválido"
docker compose --env-file "$ENV_FILE" pull odoo db 2>/dev/null || true
docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo

# Esperar healthy
max=36 i=0
while (( i < max )); do
  if docker inspect --format '{{.State.Health.Status}}' "$(hellenia_container "$COMPOSE_PROJECT_NAME" odoo)" 2>/dev/null | grep -q healthy; then
    break
  fi
  sleep 5
  ((i++)) || true
done

# --- Gate 7: Healthcheck PROD ---
log "Healthcheck PROD post-promoción..."
if ! "$SCRIPT_DIR/healthcheck-full.sh" prod 2>&1 | tee -a "$LOG_FILE"; then
  abort "Healthcheck PROD falló — ejecutar rollback: restore-hellenia-prod.sh $BACKUP_DIR"
fi

# --- Gate 8: Smoke test URL principal ---
CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "https://${ODOO_PUBLIC_HOST}/web/login" 2>/dev/null || echo "000")
if [[ "$CODE" != "200" ]]; then
  abort "Smoke test falló: https://${ODOO_PUBLIC_HOST}/web/login → HTTP $CODE"
fi
log "OK  Smoke test: HTTP $CODE"

log "=== PROMOCIÓN COMPLETADA ==="
log "Commit: $CERTIFIED_COMMIT"
log "URL: https://${ODOO_PUBLIC_HOST}"
log "Backup rollback: $BACKUP_DIR"
log "Log: $LOG_FILE"
