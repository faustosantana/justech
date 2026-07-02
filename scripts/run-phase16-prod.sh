#!/usr/bin/env bash
# Fase 16 — Go-Live producción: backup + importación + validación
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
IMPORT_DIR="$PROJECT_ROOT/data/hellenia/import"
EVIDENCE="$PROJECT_ROOT/evidence/phase16-go-live-prod.json"
LOG="$PROJECT_ROOT/logs/deploy/phase16-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$EVIDENCE")" "$(dirname "$LOG")" "$IMPORT_DIR"

if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  git pull origin "$(git branch --show-current)" 2>/dev/null || true
  rsync -av "${REPO}/custom/" "${PROJECT_ROOT}/custom/"
  rsync -av "${REPO}/scripts/" "${PROJECT_ROOT}/scripts/"
  rsync -av "${REPO}/data/hellenia/" "${PROJECT_ROOT}/data/hellenia/"
  chmod +x "${PROJECT_ROOT}/scripts/"*.sh
fi

hellenia_log "=== Fase 16 — Backup PROD ===" | tee "$LOG"
"$SCRIPT_DIR/backup-hellenia-prod.sh" 2>&1 | tee -a "$LOG"

hellenia_load_env "$ENV_FILE"
export HELLENIA_IMPORT_DIR="$IMPORT_DIR"
# SMTP vars from .env if present
set -a
# shellcheck disable=SC1090
source "$ENV_FILE" 2>/dev/null || true
set +a

hellenia_log "=== Fase 16 — Go-Live script ===" | tee -a "$LOG"
hellenia_log "Import dir: $IMPORT_DIR" | tee -a "$LOG"
ls -la "$IMPORT_DIR" 2>&1 | tee -a "$LOG" || true

"$SCRIPT_DIR/run-odoo-shell-env.sh" prod phase16-go-live-prod.py PHASE16_GOLIVE "$EVIDENCE" 2>&1 | tee -a "$LOG"

python3 -c "
import json
d = json.load(open('$EVIDENCE'))
print('ok:', d.get('ok'))
print('pending:', len(d.get('pending_client', [])))
for p in d.get('pending_client', []):
    print(' -', p)
"

if python3 -c "import json; d=json.load(open('$EVIDENCE')); exit(0 if d.get('ok') else 1)"; then
  hellenia_log "PASS Fase 16 — $EVIDENCE" | tee -a "$LOG"
else
  hellenia_log "FAIL Fase 16 (pendientes cliente) — $EVIDENCE" | tee -a "$LOG"
  exit 1
fi
