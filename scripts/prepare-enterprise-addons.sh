#!/usr/bin/env bash
# Copia solo módulos Enterprise (no presentes en imagen Community) a enterprise/addons/
# Uso: prepare-enterprise-addons.sh [ruta-odoo-19.0+e.*/]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BASE_IMAGE="${BASE_IMAGE:-odoo:19.0-20260619}"
EXTRACTED="${1:-}"

if [[ -z "$EXTRACTED" ]]; then
  EXTRACTED=$(find "$PROJECT_ROOT/enterprise" -maxdepth 1 -type d -name 'odoo-19.0+e.*' | head -1)
fi

[[ -d "$EXTRACTED/odoo/addons" ]] || {
  hellenia_log "ERROR: ruta inválida: $EXTRACTED"
  exit 1
}

DEST="$PROJECT_ROOT/enterprise/addons"
SRC="$EXTRACTED/odoo/addons"
LOG_FILE="$PROJECT_ROOT/logs/deploy/prepare-enterprise-addons-$(date +%Y-%m-%d_%H%M).log"
mkdir -p "$(dirname "$LOG_FILE")"

hellenia_log "Comparando addons +e vs $BASE_IMAGE" | tee -a "$LOG_FILE"

COMM_LIST=$(mktemp)
ENT_LIST=$(mktemp)
trap 'rm -f "$COMM_LIST" "$ENT_LIST"' EXIT

docker run --rm "$BASE_IMAGE" ls /usr/lib/python3/dist-packages/odoo/addons | sort > "$COMM_LIST"
ls -1 "$SRC" | sort > "$ENT_LIST"

mkdir -p "$DEST"
# Limpiar addons previos (preservar README.md en enterprise/ raíz)
find "$DEST" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true

COUNT=0
while IFS= read -r mod; do
  [[ -d "$SRC/$mod" ]] || continue
  [[ -f "$SRC/$mod/__manifest__.py" ]] || continue
  if ! grep -qx "$mod" "$COMM_LIST"; then
    rsync -a "$SRC/$mod/" "$DEST/$mod/"
    COUNT=$((COUNT + 1))
  fi
done < "$ENT_LIST"

[[ -f "$DEST/web_enterprise/__manifest__.py" ]] || {
  hellenia_log "ERROR: web_enterprise no copiado a $DEST"
  exit 1
}

hellenia_log "OK  $COUNT módulos Enterprise en $DEST" | tee -a "$LOG_FILE"
hellenia_log "web_enterprise: $(grep version "$DEST/web_enterprise/__manifest__.py" | head -1)" | tee -a "$LOG_FILE"
