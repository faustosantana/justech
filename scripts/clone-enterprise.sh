#!/usr/bin/env bash
# Clona repositorio oficial odoo/enterprise rama 19.0 (Fase E1)
# Autenticación preferida: SSH key dedicada (ver docs/E0.6-GITHUB-ENTERPRISE.md)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENTERPRISE_DIR="$PROJECT_ROOT/enterprise"
BRANCH="19.0"
CRED_DIR="$PROJECT_ROOT/config/credentials"
SSH_CONFIG="$CRED_DIR/ssh_config"
SSH_KEY="$CRED_DIR/github_ed25519"
CRED_FILE="$CRED_DIR/github.env"
LOG_FILE="$PROJECT_ROOT/logs/deploy/clone-enterprise-$(date +%Y-%m-%d_%H%M).log"
REPO_SSH="git@github.com:odoo/enterprise.git"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

mkdir -p "$(dirname "$LOG_FILE")" "$CRED_DIR"

git_ssh() {
  if [[ -f "$SSH_CONFIG" ]]; then
    echo "ssh -F $SSH_CONFIG -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
  elif [[ -f "$SSH_KEY" ]]; then
    echo "ssh -i $SSH_KEY -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
  else
    echo ""
  fi
}

if [[ -f "$ENTERPRISE_DIR/.git/HEAD" ]]; then
  log "enterprise/ ya existe — actualizando"
  SSH_CMD="$(git_ssh)"
  if [[ -n "$SSH_CMD" ]]; then
    GIT_SSH_COMMAND="$SSH_CMD" git -C "$ENTERPRISE_DIR" fetch origin "$BRANCH"
    git -C "$ENTERPRISE_DIR" checkout "$BRANCH"
    GIT_SSH_COMMAND="$SSH_CMD" git -C "$ENTERPRISE_DIR" pull origin "$BRANCH"
  else
    log "WARN Sin SSH config — intentando pull sin credenciales"
    git -C "$ENTERPRISE_DIR" fetch origin "$BRANCH"
    git -C "$ENTERPRISE_DIR" checkout "$BRANCH"
    git -C "$ENTERPRISE_DIR" pull origin "$BRANCH"
  fi
  log "Actualizado: $(git -C "$ENTERPRISE_DIR" rev-parse --short HEAD)"
  exit 0
fi

# --- Autenticación: SSH preferido, PAT fallback ---
SSH_CMD="$(git_ssh)"
if [[ -n "$SSH_CMD" ]]; then
  log "Autenticación: SSH key dedicada"
  log "Verificando acceso a $REPO_SSH rama $BRANCH"
  GIT_SSH_COMMAND="$SSH_CMD" git ls-remote "$REPO_SSH" "refs/heads/$BRANCH" >/dev/null
  log "Clonando $REPO_SSH rama $BRANCH → $ENTERPRISE_DIR"
  GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="$SSH_CMD" git clone \
    "$REPO_SSH" --branch "$BRANCH" --depth 1 "$ENTERPRISE_DIR"
elif [[ -f "$CRED_FILE" ]]; then
  log "WARN Autenticación: PAT fallback (preferir SSH)"
  # shellcheck disable=SC1090
  source "$CRED_FILE"
  if [[ -z "${GITHUB_USER:-}" || -z "${GITHUB_TOKEN:-}" ]]; then
    log "ERROR: GITHUB_USER y GITHUB_TOKEN requeridos en $CRED_FILE"
    exit 1
  fi
  GIT_TERMINAL_PROMPT=0 git clone \
    "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/odoo/enterprise.git" \
    --branch "$BRANCH" --depth 1 "$ENTERPRISE_DIR"
else
  log "ERROR: Configurar SSH key en $CRED_DIR"
  log "  - github_ed25519 + ssh_config (preferido)"
  log "  - o github.env con PAT (fallback)"
  log "Ver docs/E0.6-GITHUB-ENTERPRISE.md y config/credentials/README.md"
  exit 1
fi

log "Commit: $(git -C "$ENTERPRISE_DIR" rev-parse --short HEAD)"

for mod in l10n_do_edi l10n_do_reports web_enterprise; do
  if [[ -f "$ENTERPRISE_DIR/$mod/__manifest__.py" ]]; then
    log "OK  módulo $mod presente"
  else
    log "WARN módulo $mod no encontrado en rama $BRANCH"
  fi
done

log "Clone completado"
