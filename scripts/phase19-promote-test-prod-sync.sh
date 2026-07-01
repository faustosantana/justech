#!/usr/bin/env bash
# Fase 19 — Sincronización controlada TEST → PRODUCCIÓN
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
CERTIFIED_COMMIT="${CERTIFIED_COMMIT:-bbaf113}"
CERTIFIED_BRANCH="${CERTIFIED_BRANCH:-cursor/phase18-13-native-payment-rebuild-dd85}"
EVIDENCE_TEST="${EVIDENCE_TEST:-$PROJECT_ROOT/evidence/phase18-13-final-payment-retention-test.json}"
TS=$(date +%Y-%m-%d_%H%M)
LOG_FILE="$PROJECT_ROOT/logs/deploy/phase19-promote-${TS}.log"
SYNC_JSON="$PROJECT_ROOT/evidence/phase19-test-prod-sync.json"

MODULES=(
  hellenia_account
  hellenia_ui
  hellenia_reports
  justech_l10n_do_base
  justech_l10n_do_ncf
  justech_l10n_do_reports
)

mkdir -p "$(dirname "$LOG_FILE")" "$PROJECT_ROOT/evidence" "$PROJECT_ROOT/docs"

log() { hellenia_log "$*" | tee -a "$LOG_FILE"; }

abort() {
  log "ABORT FASE 19: $*"
  exit 1
}

log "=== FASE 19 — Sincronización TEST → PRODUCCIÓN ==="

if [[ "${APPROVE_PROMOTION:-}" != "1" ]]; then
  abort "Requiere APPROVE_PROMOTION=1"
fi

if [[ ! -f "$EVIDENCE_TEST" ]]; then
  abort "Sin evidencia TEST: $EVIDENCE_TEST"
fi
python3 -c "
import json, sys
d=json.load(open('$EVIDENCE_TEST'))
if not d.get('pass') and not d.get('ok'):
    sys.exit(1)
print('TEST evidence PASS:', d.get('summary', d.get('phase')))
" || abort "Evidencia TEST no PASS: $EVIDENCE_TEST"

# Guardar estado PROD pre-promoción
PROD_COMMIT_BEFORE=""
if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  PROD_COMMIT_BEFORE=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
  git fetch origin "$CERTIFIED_BRANCH" 2>/dev/null || true
  git checkout "$CERTIFIED_BRANCH" || abort "Branch $CERTIFIED_BRANCH no encontrada"
  git pull origin "$CERTIFIED_BRANCH" || true
  git checkout "$CERTIFIED_COMMIT" 2>/dev/null || git checkout "$CERTIFIED_BRANCH"
  ACTUAL=$(git rev-parse HEAD)
  log "Commit certificado: $ACTUAL ($(git log -1 --oneline))"
else
  abort "Sin repositorio Git en $REPO"
fi

# Manifest pre-promoción
PRE_MANIFEST="$PROJECT_ROOT/backups/hellenia-prod/pre-promotion-${TS}.json"
mkdir -p "$(dirname "$PRE_MANIFEST")"
source "$PROJECT_ROOT/config/test/.env" 2>/dev/null || true
cat > "$PRE_MANIFEST" << EOF
{
  "timestamp": "$TS",
  "repo_commit_before": "$PROD_COMMIT_BEFORE",
  "certified_commit": "$ACTUAL",
  "certified_branch": "$CERTIFIED_BRANCH",
  "evidence_test": "$EVIDENCE_TEST"
}
EOF

# Backup PROD obligatorio
log "Backup producción..."
if ! "$SCRIPT_DIR/backup-hellenia-prod.sh" 2>&1 | tee -a "$LOG_FILE"; then
  abort "Backup PROD falló"
fi
BACKUP_DIR=$(ls -1dt "${PROJECT_ROOT}/backups/hellenia-prod"/20* 2>/dev/null | head -1)
log "Backup: $BACKUP_DIR"
echo "backup_dir=$BACKUP_DIR" >> "$PRE_MANIFEST"

# Versiones módulos PROD pre-upgrade
hellenia_load_env "$ENV_FILE"
PRE_MODS="$BACKUP_DIR/modules_pre_upgrade.txt"
docker exec hellenia-prod-db-1 psql -U "${DB_USER}" -d "${ODOO_DB_NAME}" -tAc \
  "SELECT name||'|'||state||'|'||latest_version FROM ir_module_module WHERE name IN ('hellenia_account','hellenia_ui','hellenia_reports','justech_l10n_do_base','justech_l10n_do_ncf','justech_l10n_do_reports') ORDER BY name;" \
  > "$PRE_MODS" 2>/dev/null || true
cp "$PRE_MODS" "$BACKUP_DIR/"

# Sincronizar artefactos
log "Sincronizando custom/ desde repo certificado..."
hellenia_sync_from_repo "$REPO" "$PROJECT_ROOT"

# Upgrade módulos
cd "$COMPOSE_DIR"
hellenia_load_env "$ENV_FILE"

for mod in "${MODULES[@]}"; do
  state=$(docker exec hellenia-prod-db-1 psql -U "${DB_USER}" -d "${ODOO_DB_NAME}" -tAc \
    "SELECT state FROM ir_module_module WHERE name='${mod}'" 2>/dev/null | tr -d '[:space:]' || true)
  if [[ "$state" == "installed" ]]; then
    log "Upgrade módulo: $mod"
    docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
      -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
      -u "$mod" --stop-after-init --no-http 2>&1 | tail -8 | tee -a "$LOG_FILE"
  else
    log "Instalar módulo: $mod (estado=$state)"
    docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
      -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
      -i "$mod" --stop-after-init --no-http 2>&1 | tail -8 | tee -a "$LOG_FILE"
  fi
done

log "Reiniciando Odoo producción..."
docker compose --env-file "$ENV_FILE" up -d --force-recreate odoo
sleep 20

max=24 i=0
while (( i < max )); do
  if docker inspect --format '{{.State.Health.Status}}' hellenia-prod-odoo-1 2>/dev/null | grep -q healthy; then
    break
  fi
  sleep 5
  ((i++)) || true
done

# Validación PROD
log "Validación post-sync PROD..."
if ! "$SCRIPT_DIR/run-odoo-shell-env.sh" prod phase19-prod-post-sync-validation.py PHASE19PROD \
  "$SYNC_JSON" 2>&1 | tee -a "$LOG_FILE"; then
  log "FAIL validación PROD — rollback: $SCRIPT_DIR/restore-hellenia-prod.sh $BACKUP_DIR"
  abort "Validación PROD falló — ejecutar rollback"
fi

# Healthcheck + smoke
if ! "$SCRIPT_DIR/healthcheck-full.sh" prod 2>&1 | tee -a "$LOG_FILE"; then
  abort "Healthcheck PROD falló — rollback: $SCRIPT_DIR/restore-hellenia-prod.sh $BACKUP_DIR"
fi

CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 25 "https://prod.hellenia.cloud/web/login" 2>/dev/null || echo "000")
if [[ "$CODE" != "200" && "$CODE" != "303" ]]; then
  abort "Smoke login falló HTTP $CODE — rollback: $SCRIPT_DIR/restore-hellenia-prod.sh $BACKUP_DIR"
fi
log "Smoke test login: HTTP $CODE"

# Enriquecer JSON evidencia
python3 << PY
import json
from pathlib import Path
p = Path("$SYNC_JSON")
d = json.loads(p.read_text()) if p.exists() else {}
d.update({
    "promotion": {
        "commit": "$ACTUAL",
        "branch": "$CERTIFIED_BRANCH",
        "backup": "$BACKUP_DIR",
        "commit_before": "$PROD_COMMIT_BEFORE",
        "modules_upgraded": $(printf '%s\n' "${MODULES[@]}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip().split()))'),
        "log": "$LOG_FILE",
        "smoke_http": "$CODE",
    },
    "rollback_command": "$SCRIPT_DIR/restore-hellenia-prod.sh $BACKUP_DIR",
})
p.write_text(json.dumps(d, ensure_ascii=False, indent=2))
print("Evidencia:", p)
PY

log "=== FASE 19 PROMOCIÓN COMPLETADA ==="
log "Commit: $ACTUAL"
log "Backup: $BACKUP_DIR"
log "Evidencia: $SYNC_JSON"
