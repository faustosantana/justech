#!/usr/bin/env bash
# Valida tarball Enterprise del portal sin extraer a enterprise/
# Uso: validate-enterprise-archive.sh [archivo.tar.gz]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOWNLOAD_DIR="$PROJECT_ROOT/downloads/enterprise"
ARCHIVE="${1:-}"

if [[ -z "$ARCHIVE" ]]; then
  ARCHIVE=$(find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' \) 2>/dev/null | head -1)
fi

[[ -f "$ARCHIVE" ]] || { hellenia_log "ERROR: Archivo no encontrado: $ARCHIVE"; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

hellenia_log "Validando: $ARCHIVE"

case "$ARCHIVE" in
  *.zip) unzip -q "$ARCHIVE" -d "$WORK" ;;
  *.tar.gz|*.tgz) tar xzf "$ARCHIVE" -C "$WORK" ;;
  *) hellenia_log "ERROR: formato no soportado"; exit 1 ;;
esac

FOUND=$(find "$WORK" -type f -path '*/web_enterprise/__manifest__.py' | head -1)
if [[ -n "$FOUND" ]]; then
  hellenia_log "OK  web_enterprise encontrado en archivo"
  hellenia_log "OK  archivo listo para extract-enterprise-portal.sh"
  exit 0
fi

hellenia_log "FAIL web_enterprise no encontrado en archivo"
exit 1
