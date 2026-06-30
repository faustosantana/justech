#!/usr/bin/env bash
# Clona repositorio oficial odoo/enterprise rama 19.0 (Fase E1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENTERPRISE_DIR="$PROJECT_ROOT/enterprise"
BRANCH="19.0"
CRED_FILE="$PROJECT_ROOT/config/credentials/github.env"
LOG_FILE="$PROJECT_ROOT/logs/deploy/clone-enterprise-$(date +%Y-%m-%d_%H%M).log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")" "$PROJECT_ROOT/config/credentials"

if [[ -f "$ENTERPRISE_DIR/.git/HEAD" ]]; then
  log "enterprise/ ya existe — actualizando"
  git -C "$ENTERPRISE_DIR" fetch origin "$BRANCH"
  git -C "$ENTERPRISE_DIR" checkout "$BRANCH"
  git -C "$ENTERPRISE_DIR" pull origin "$BRANCH"
  log "Actualizado: $(git -C "$ENTERPRISE_DIR" rev-parse --short HEAD)"
  exit 0
fi

if [[ ! -f "$CRED_FILE" ]]; then
  log "ERROR: Crear $CRED_FILE desde github.env.example"
  log "Ver docs/E0.6-GITHUB-ENTERPRISE.md"
  exit 1
fi

# shellcheck disable=SC1090
source "$CRED_FILE"

if [[ -z "${GITHUB_USER:-}" || -z "${GITHUB_TOKEN:-}" ]]; then
  log "ERROR: GITHUB_USER y GITHUB_TOKEN requeridos en $CRED_FILE"
  exit 1
fi

log "Clonando odoo/enterprise rama $BRANCH → $ENTERPRISE_DIR"
GIT_TERMINAL_PROMPT=0 git clone \
  "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/odoo/enterprise.git" \
  --branch "$BRANCH" --depth 1 "$ENTERPRISE_DIR"

log "Commit: $(git -C "$ENTERPRISE_DIR" rev-parse --short HEAD)"

for mod in l10n_do_edi l10n_do_reports web_enterprise; do
  if [[ -f "$ENTERPRISE_DIR/$mod/__manifest__.py" ]]; then
    log "OK  módulo $mod presente"
  else
    log "WARN módulo $mod no encontrado en rama $BRANCH"
  fi
done

log "Clone completado"
