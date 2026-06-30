#!/usr/bin/env bash
# Obtiene código Enterprise — Git (si disponible) o portal tarball (fallback)
# Uso: fetch-enterprise.sh [--portal-only|--git-only] [ruta.tar.gz]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

MODE="auto"
ARCHIVE=""

for arg in "$@"; do
  case "$arg" in
    --portal-only) MODE="portal" ;;
    --git-only) MODE="git" ;;
    --*) hellenia_log "ERROR: opción desconocida $arg"; exit 1 ;;
    *) ARCHIVE="$arg" ;;
  esac
done

if [[ "$MODE" == "portal" ]]; then
  exec "${SCRIPT_DIR}/extract-enterprise-portal.sh" ${ARCHIVE:+"$ARCHIVE"}
fi

if [[ "$MODE" == "git" ]]; then
  exec "${SCRIPT_DIR}/clone-enterprise.sh"
fi

# auto
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_CONFIG="$PROJECT_ROOT/config/credentials/ssh_config"

if [[ -f "$SSH_CONFIG" ]]; then
  hellenia_log "Intentando acceso Git odoo/enterprise..."
  if GIT_SSH_COMMAND="ssh -F $SSH_CONFIG -o BatchMode=yes" \
    git ls-remote git@github.com:odoo/enterprise.git refs/heads/19.0 &>/dev/null; then
    hellenia_log "Git disponible — usando clone-enterprise.sh"
    exec "${SCRIPT_DIR}/clone-enterprise.sh"
  fi
  hellenia_log "WARN Git no disponible — usando tarball portal"
fi

exec "${SCRIPT_DIR}/extract-enterprise-portal.sh" ${ARCHIVE:+"$ARCHIVE"}
