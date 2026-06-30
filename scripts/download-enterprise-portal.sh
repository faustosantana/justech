#!/usr/bin/env bash
# Descarga Enterprise desde enlace temporal del portal Odoo (semi-automático)
# NO requiere subir archivo manualmente al VPS si el enlace es directo y vigente.
#
# Uso:
#   download-enterprise-portal.sh 'https://...' 
#   ODOO_DOWNLOAD_URL='https://...' download-enterprise-portal.sh
#
# El usuario obtiene el enlace:
#   1. Login odoo.com → page/download → Enterprise Sources 19
#   2. Clic derecho en Download → "Copiar dirección del enlace"
#   3. Pegar URL en Cursor (NO guardar en Git)
#
# Ver docs/E0.6c-ENTERPRISE-DELIVERY-FLOW.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOWNLOAD_DIR="$PROJECT_ROOT/downloads/enterprise"
URL="${1:-${ODOO_DOWNLOAD_URL:-}}"
OUT="${ODOO_DOWNLOAD_FILE:-$DOWNLOAD_DIR/odoo-19.0-enterprise-sources.tar.gz}"
LOG_FILE="$PROJECT_ROOT/logs/deploy/download-enterprise-portal-$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$DOWNLOAD_DIR" "$(dirname "$LOG_FILE")"

if [[ -z "$URL" ]]; then
  hellenia_log "ERROR: Falta URL de descarga"
  hellenia_log ""
  hellenia_log "Odoo NO publica URL wget permanente sin sesión."
  hellenia_log "Opciones:"
  hellenia_log "  A) Pegar enlace temporal: $0 'https://...'"
  hellenia_log "  B) Adjuntar archivo a Cursor → scripts/receive-enterprise-archive.sh"
  hellenia_log ""
  hellenia_log "Ver docs/E0.6c-ENTERPRISE-DELIVERY-FLOW.md"
  exit 1
fi

hellenia_log "Descargando Enterprise → $OUT" | tee -a "$LOG_FILE"
hellenia_log "URL: ${URL:0:80}..." | tee -a "$LOG_FILE"

TMP="${OUT}.part"
if ! curl -fSL --max-time 900 --retry 2 --retry-delay 5 \
  -o "$TMP" "$URL" 2>>"$LOG_FILE"; then
  rm -f "$TMP"
  hellenia_log "ERROR: curl falló — enlace expirado, requiere login, o URL incorrecta"
  hellenia_log "Obtener nuevo enlace desde portal (válido minutos) o usar receive-enterprise-archive.sh"
  exit 1
fi

mv "$TMP" "$OUT"
chmod 600 "$OUT"

SIZE=$(stat -c%s "$OUT" 2>/dev/null || stat -f%z "$OUT")
hellenia_log "Descargado: $SIZE bytes" | tee -a "$LOG_FILE"

if [[ "$SIZE" -lt 500000 ]]; then
  hellenia_log "WARN: archivo muy pequeño — puede ser HTML de error, no tarball"
  file "$OUT" | tee -a "$LOG_FILE"
fi

hellenia_log "Validando..."
if "${SCRIPT_DIR}/validate-enterprise-archive.sh" "$OUT"; then
  hellenia_log "OK  listo para extract-enterprise-portal.sh (tras aprobación E1a)"
else
  hellenia_log "FAIL validación — revisar archivo"
  exit 1
fi
