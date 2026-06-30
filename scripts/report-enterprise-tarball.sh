#!/usr/bin/env bash
# Reporte de estructura de tarball Enterprise/Odoo — sin extraer ni instalar
# Uso: report-enterprise-tarball.sh /path/archivo.tar.gz [--json]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ARCHIVE="${1:?Uso: report-enterprise-tarball.sh <archivo.tar.gz>}"
JSON=false
[[ "${2:-}" == "--json" ]] && JSON=true

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="$PROJECT_ROOT/logs/validate"
STAMP=$(date +%Y-%m-%d_%H%M%S)
mkdir -p "$REPORT_DIR"

hellenia_require_file "$ARCHIVE"

SHA=$(sha256sum "$ARCHIVE" | awk '{print $1}')
SIZE=$(stat -c%s "$ARCHIVE" 2>/dev/null || stat -f%z "$ARCHIVE")

# Integridad
if ! tar tzf "$ARCHIVE" >/dev/null 2>&1; then
  hellenia_log "ERROR: archivo corrupto"
  exit 1
fi

TOTAL=$(tar tzf "$ARCHIVE" | wc -l)
TOP=$(tar tzf "$ARCHIVE" | awk -F/ 'NF==2 && $2=="" {print $1}' | sort -u | head -5)
ROOT=$(echo "$TOP" | head -1)

# Marcadores estructura
HAS_ODOO_BIN=$(tar tzf "$ARCHIVE" | grep -cE '(^|/)odoo-bin$' || true)
HAS_SETUP=$(tar tzf "$ARCHIVE" | grep -cE '(^|/)setup\.py$' || true)
HAS_RELEASE=$(tar tzf "$ARCHIVE" | grep -cE 'odoo/release\.py$' || true)
WEB_ENT=$(tar tzf "$ARCHIVE" | grep -E 'web_enterprise/__manifest__\.py$' | head -1)
ADDONS_WEB=$(tar tzf "$ARCHIVE" | grep -E 'odoo/addons/web_enterprise/__manifest__\.py$' | head -1)
ENTERPRISE_ONLY=$(tar tzf "$ARCHIVE" | grep -E '(^|/)enterprise/|^|/)addons/web_enterprise' | head -3)

# Versión desde release.py si existe
VERSION_MAJOR=""
if [[ -n "$ROOT" && "$HAS_RELEASE" -gt 0 ]]; then
  VERSION_MAJOR=$(tar xzf "$ARCHIVE" -O "${ROOT}/odoo/release.py" 2>/dev/null | python3 -c "
import sys, re
text = sys.stdin.read()
m = re.search(r'version_info\s*=\s*\((\d+)', text)
print(m.group(1) if m else '')
" 2>/dev/null || echo "")
fi

# Clasificación
TYPE="unknown"
STRATEGY=""
if [[ "$HAS_ODOO_BIN" -gt 0 || "$HAS_SETUP" -gt 0 ]] && [[ -n "$ADDONS_WEB" ]]; then
  TYPE="full_enterprise_source"
  STRATEGY="Tarball Odoo COMPLETO + Enterprise (+e). Extraer a enterprise/. Para Docker: copiar solo addons Enterprise (diff vs imagen Community) a enterprise/addons/ y hornear en imagen hellenia-odoo:19-enterprise. NO reemplazar servidor Community de la imagen base."
elif [[ -n "$WEB_ENT" && "$HAS_ODOO_BIN" -eq 0 ]]; then
  TYPE="enterprise_addons_only"
  STRATEGY="Solo addons Enterprise. Extraer directamente a enterprise/addons/ y hornear en imagen o montar (según política)."
else
  TYPE="needs_manual_review"
  STRATEGY="Estructura no estándar — revisar listado top-level antes de E1a."
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
  echo ""
  echo "--- Marcadores ---"
  echo "odoo-bin: $HAS_ODOO_BIN"
  echo "setup.py: $HAS_SETUP"
  echo "odoo/release.py: $HAS_RELEASE"
  echo "web_enterprise (odoo/addons): ${ADDONS_WEB:-no}"
  echo "web_enterprise (otra ruta): ${WEB_ENT:-no}"
  echo ""
  echo "--- Top-level (primeros 20) ---"
  tar tzf "$ARCHIVE" | awk -F/ 'NF==2 {print $1}' | sort -u | head -20
  echo ""
  echo "--- Estrategia recomendada ---"
  echo "$STRATEGY"
} | tee "$REPORT_FILE"

if $JSON; then
  python3 - "$REPORT_FILE" << 'PY'
import json, sys
data = {}
for line in open(sys.argv[1]):
    if ": " in line and not line.startswith("---"):
        k, v = line.split(": ", 1)
        data[k.strip()] = v.strip()
print(json.dumps(data, indent=2))
PY
fi

hellenia_log "Reporte guardado: $REPORT_FILE"
