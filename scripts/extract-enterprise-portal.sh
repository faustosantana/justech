#!/usr/bin/env bash
# Extrae código Enterprise desde tarball oficial del portal Odoo
# Uso: extract-enterprise-portal.sh [/path/to/enterprise-sources.tar.gz]
# Ver docs/E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENTERPRISE_DIR="$PROJECT_ROOT/enterprise"
DOWNLOAD_DIR="$PROJECT_ROOT/downloads/enterprise"
LOG_FILE="$PROJECT_ROOT/logs/deploy/extract-enterprise-portal-$(date +%Y-%m-%d_%H%M).log"
BRANCH_TARGET="19.0"

ARCHIVE="${1:-}"
if [[ -z "$ARCHIVE" ]]; then
  ARCHIVE=$(find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' \) -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
fi

mkdir -p "$(dirname "$LOG_FILE")" "$DOWNLOAD_DIR" "$ENTERPRISE_DIR"

if [[ -z "$ARCHIVE" || ! -f "$ARCHIVE" ]]; then
  hellenia_log "ERROR: Archivo Enterprise no encontrado"
  hellenia_log "Colocar tarball en $DOWNLOAD_DIR/"
  hellenia_log "Uso: $0 /path/to/odoo-19-enterprise-sources.tar.gz"
  exit 1
fi

hellenia_log "Extrayendo Enterprise desde: $ARCHIVE" | tee -a "$LOG_FILE"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

case "$ARCHIVE" in
  *.zip)
    unzip -q "$ARCHIVE" -d "$WORK"
    ;;
  *.tar.gz|*.tgz)
    tar xzf "$ARCHIVE" -C "$WORK"
    ;;
  *)
    hellenia_log "ERROR: Formato no soportado (use .tar.gz o .zip)"
    exit 1
    ;;
esac

# Localizar directorio con web_enterprise (addons Enterprise)
SRC=""
if [[ -f "$WORK/web_enterprise/__manifest__.py" ]]; then
  SRC="$WORK"
else
  SRC=$(find "$WORK" -type f -path '*/web_enterprise/__manifest__.py' -print -quit 2>/dev/null | sed 's|/web_enterprise/__manifest__.py||')
fi

if [[ -z "$SRC" || ! -f "$SRC/web_enterprise/__manifest__.py" ]]; then
  hellenia_log "ERROR: No se encontró web_enterprise en el archivo"
  hellenia_log "Contenido top-level:"
  ls -la "$WORK" | tee -a "$LOG_FILE"
  exit 1
fi

hellenia_log "Origen módulos: $SRC" | tee -a "$LOG_FILE"

# Preservar README si existe; limpiar resto (incl. .git legacy)
if [[ -f "$ENTERPRISE_DIR/README.md" ]]; then
  cp "$ENTERPRISE_DIR/README.md" "$WORK/README.md.bak"
fi
find "$ENTERPRISE_DIR" -mindepth 1 -maxdepth 1 ! -name 'README.md' -exec rm -rf {} + 2>/dev/null || true

rsync -a "$SRC"/ "$ENTERPRISE_DIR"/
[[ -f "$WORK/README.md.bak" ]] && mv "$WORK/README.md.bak" "$ENTERPRISE_DIR/README.md"

# Manifest de procedencia (portal no tiene commit Git)
cat > "$ENTERPRISE_DIR/MANIFEST.txt" << EOF
source=odoo_portal_download
archive=$(basename "$ARCHIVE")
archive_path=$ARCHIVE
extracted_at=$(date -Iseconds)
target_version=$BRANCH_TARGET
web_enterprise=$(test -f "$ENTERPRISE_DIR/web_enterprise/__manifest__.py" && echo present || echo missing)
EOF

for mod in web_enterprise l10n_do_edi l10n_do_reports; do
  if [[ -f "$ENTERPRISE_DIR/$mod/__manifest__.py" ]]; then
    hellenia_log "OK  módulo $mod presente" | tee -a "$LOG_FILE"
  else
    hellenia_log "WARN módulo $mod no encontrado" | tee -a "$LOG_FILE"
  fi
done

hellenia_log "Enterprise extraído en $ENTERPRISE_DIR" | tee -a "$LOG_FILE"
hellenia_log "Siguiente: recrear contenedor DEV e instalar web_enterprise (E1a)"
