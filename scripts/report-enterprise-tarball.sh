#!/usr/bin/env bash
# Reporte de estructura de tarball Enterprise/Odoo — un solo listado tar
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ARCHIVE="${1:?Uso: report-enterprise-tarball.sh <archivo.tar.gz>}"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="$PROJECT_ROOT/logs/validate"
STAMP=$(date +%Y-%m-%d_%H%M%S)
mkdir -p "$REPORT_DIR"

hellenia_require_file "$ARCHIVE"

SHA=$(sha256sum "$ARCHIVE" | awk '{print $1}')
SIZE=$(stat -c%s "$ARCHIVE" 2>/dev/null || stat -f%z "$ARCHIVE")

hellenia_log "Listando tarball (puede tardar ~1 min)..."
LIST=$(mktemp)
trap 'rm -f "$LIST"' EXIT

if ! tar tzf "$ARCHIVE" > "$LIST" 2>/dev/null; then
  hellenia_log "ERROR: archivo corrupto"
  exit 1
fi

TOTAL=$(wc -l < "$LIST")
ROOT=$(awk -F/ 'NF>=1 && $1!="" {print $1; exit}' "$LIST")
ADDONS_WEB=$(grep -m1 -E 'odoo/addons/web_enterprise/__manifest__\.py$' "$LIST" || true)
HAS_SETUP=$(grep -cE '(^|/)setup\.py$' "$LIST" || true)
HAS_RELEASE=$(grep -cE 'odoo/release\.py$' "$LIST" || true)

VERSION_MAJOR=""
if [[ -n "$ROOT" && "$HAS_RELEASE" -gt 0 ]]; then
  VERSION_MAJOR=$(tar xzf "$ARCHIVE" -O "${ROOT}/odoo/release.py" 2>/dev/null | python3 -c "
import sys, re
m = re.search(r'version_info\s*=\s*\((\d+)', sys.stdin.read())
print(m.group(1) if m else '')
" 2>/dev/null || echo "")
fi

TYPE="unknown"
STRATEGY=""
if [[ -n "$ADDONS_WEB" && "$VERSION_MAJOR" == "19" ]]; then
  TYPE="full_enterprise_source"
  STRATEGY="Tarball Odoo COMPLETO + Enterprise (+e). Raíz: ${ROOT}/ — servidor + addons fusionados. Estrategia: extraer completo → diff addons vs imagen Community → enterprise/addons/ (~700 módulos) → imagen hellenia-odoo:19-enterprise FROM odoo:19.0-20260619. NO sustituir servidor Community de la imagen base."
elif grep -qE 'web_enterprise/__manifest__\.py$' "$LIST" && [[ "$HAS_SETUP" -eq 0 ]]; then
  TYPE="enterprise_addons_only"
  STRATEGY="Solo addons Enterprise. Extraer a enterprise/addons/ y hornear."
else
  TYPE="needs_manual_review"
  STRATEGY="Revisar estructura manualmente."
fi

REPORT_FILE="$REPORT_DIR/tarball-structure-${STAMP}.txt"
{
  echo "=== Reporte estructura tarball Enterprise/Odoo ==="
  echo "fecha: $(date -Iseconds)"
  echo "archivo: $ARCHIVE"
  echo "nombre: $(basename "$ARCHIVE")"
  echo "tamano_bytes: $SIZE"
  echo "sha256: $SHA"
  echo "entradas_tar: $TOTAL"
  echo "raiz_top_level: $ROOT"
  echo "tipo_detectado: $TYPE"
  echo "version_major: ${VERSION_MAJOR:-desconocida}"
  echo "web_enterprise: ${ADDONS_WEB:-no}"
  echo "setup.py: $HAS_SETUP"
  echo "odoo/release.py: $HAS_RELEASE"
  echo ""
  echo "--- Top-level ---"
  awk -F/ 'NF==2 {print $1}' "$LIST" | sort -u
  echo ""
  echo "--- Estrategia recomendada ---"
  echo "$STRATEGY"
} | tee "$REPORT_FILE"

hellenia_log "Reporte: $REPORT_FILE"
