#!/usr/bin/env bash
# Extrae tarball oficial Odoo 19 Enterprise (+e) a enterprise/
# Uso: extract-enterprise-full.sh /path/odoo_19.0+e.YYYYMMDD.tar.gz
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENTERPRISE_DIR="$PROJECT_ROOT/enterprise"
ARCHIVE="${1:?Uso: extract-enterprise-full.sh <archivo.tar.gz>}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/extract-enterprise-full-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$(dirname "$LOG_FILE")" "$ENTERPRISE_DIR"
hellenia_require_file "$ARCHIVE"

hellenia_log "Extrayendo tarball +e: $ARCHIVE" | tee -a "$LOG_FILE"
hellenia_log "SHA256: $(sha256sum "$ARCHIVE" | awk '{print $1}')" | tee -a "$LOG_FILE"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

tar xzf "$ARCHIVE" -C "$WORK"

SRC=$(find "$WORK" -maxdepth 2 -type d -name 'odoo-19.0+e.*' | head -1)
[[ -n "$SRC" ]] || SRC=$(find "$WORK" -maxdepth 1 -type d ! -path "$WORK" | head -1)

[[ -f "$SRC/odoo/addons/web_enterprise/__manifest__.py" ]] || {
  hellenia_log "ERROR: no se encontró odoo/addons/web_enterprise en $SRC"
  exit 1
}

VER=$(grep -E "['\"]version['\"]" "$SRC/odoo/addons/web_enterprise/__manifest__.py" | head -1 || true)
hellenia_log "web_enterprise manifest: $VER" | tee -a "$LOG_FILE"
echo "$VER" | grep -q '19\.0' || {
  hellenia_log "ERROR: versión distinta de 19.0"
  exit 1
}

DEST_NAME=$(basename "$SRC")
DEST="$ENTERPRISE_DIR/$DEST_NAME"

if [[ -d "$DEST" ]]; then
  hellenia_log "Reemplazando extracción previa: $DEST"
  rm -rf "$DEST"
fi

mv "$SRC" "$DEST"

cat > "$ENTERPRISE_DIR/MANIFEST.txt" << EOF
source=odoo_portal_full_enterprise
archive=$(basename "$ARCHIVE")
archive_path=$ARCHIVE
sha256=$(sha256sum "$ARCHIVE" | awk '{print $1}')
extracted_at=$(date -Iseconds)
extracted_dir=$DEST
target_version=19.0
web_enterprise=present
EOF

hellenia_log "Extraído en $DEST" | tee -a "$LOG_FILE" >&2
echo "$DEST"
