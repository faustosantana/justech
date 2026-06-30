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
  hellenia_log "ERROR: no se encontró odoo/addons/web_enterprise en $SRC" >&2
  exit 1
}

# Versión Odoo desde release.py (manifest de web_enterprise usa 1.0, no 19.0)
RELEASE_FILE="$SRC/odoo/release.py"
if [[ -f "$RELEASE_FILE" ]]; then
  MAJOR=$(python3 - "$RELEASE_FILE" << 'PY'
import sys, re
text = open(sys.argv[1]).read()
m = re.search(r"version_info\s*=\s*\((\d+)", text)
print(m.group(1) if m else "")
PY
)
  [[ "$MAJOR" == "19" ]] || {
    hellenia_log "ERROR: version_info major=$MAJOR (esperado 19)" >&2
    exit 1
  }
  hellenia_log "OK  Odoo serie $MAJOR.0 (release.py)" | tee -a "$LOG_FILE" >&2
else
  echo "$(basename "$ARCHIVE")" | grep -qE '19\.0' || {
    hellenia_log "ERROR: no release.py y nombre sin 19.0" >&2
    exit 1
  }
  hellenia_log "OK  versión 19.0 por nombre archivo" | tee -a "$LOG_FILE" >&2
fi

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
