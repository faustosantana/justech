#!/usr/bin/env bash
# Actualiza repositorio Enterprise (git pull en enterprise/)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

BRANCH="${1:-19.0}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

hellenia_log "=== Upgrade Enterprise rama ${BRANCH} ==="
BRANCH="$BRANCH" "${SCRIPT_DIR}/clone-enterprise.sh"

hellenia_log "Reiniciar Odoo manualmente o con: docker compose restart odoo"
hellenia_log "Aplicar -u solo si release notes Odoo lo indican"
