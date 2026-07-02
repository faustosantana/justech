#!/usr/bin/env bash
# Fase 14.1 — Corregir menús Contabilidad y permisos (TEST o PROD)
# Uso: run-phase14-1-fix.sh test|prod
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: run-phase14-1-fix.sh test|prod}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPO="${REPO_PATH:-$PROJECT_ROOT/repository}"
ENV_DIR="$(hellenia_env_dir "$ENV_NAME")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_DIR}/.env"
EVIDENCE="$PROJECT_ROOT/evidence/phase14-1-accounting-permissions-${ENV_NAME}.json"
LOG="$PROJECT_ROOT/logs/deploy/phase14-1-${ENV_NAME}-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$EVIDENCE")" "$(dirname "$LOG")"

if [[ -d "$REPO/.git" ]]; then
  cd "$REPO"
  git pull origin "$(git branch --show-current)" 2>/dev/null || true
  rsync -av "${REPO}/custom/" "${PROJECT_ROOT}/custom/"
  rsync -av "${REPO}/scripts/" "${PROJECT_ROOT}/scripts/"
  chmod +x "${PROJECT_ROOT}/scripts/"*.sh
fi

hellenia_load_env "$ENV_FILE"
COMPOSE_DIR="$PROJECT_ROOT/docker/${ENV_DIR}"

hellenia_log "=== Fase 14.1 — $ENV_NAME ===" | tee "$LOG"

cd "$COMPOSE_DIR"
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" \
  -u hellenia_ui --stop-after-init --no-http 2>&1 | tail -5 | tee -a "$LOG"

docker compose --env-file "$ENV_FILE" up -d odoo
sleep 12

"$SCRIPT_DIR/run-odoo-shell-env.sh" "$ENV_NAME" phase14-1-fix-accounting-permissions.py PHASE14_1 "$EVIDENCE" 2>&1 | tee -a "$LOG"

python3 -c "import json; d=json.load(open('$EVIDENCE')); exit(0 if d.get('ok') else 1)"

hellenia_log "PASS Fase 14.1 $ENV_NAME — $EVIDENCE" | tee -a "$LOG"
