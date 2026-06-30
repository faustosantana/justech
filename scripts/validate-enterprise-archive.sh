#!/usr/bin/env bash
# Valida tarball Enterprise del portal sin extraer a enterprise/
# Uso:
#   validate-enterprise-archive.sh [archivo.tar.gz]
#   validate-enterprise-archive.sh [archivo] --report
#   validate-enterprise-archive.sh [archivo] --json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOWNLOAD_DIR="$PROJECT_ROOT/downloads/enterprise"
VALIDATOR="${SCRIPT_DIR}/lib/validate_enterprise_archive.py"
REPORT_DIR="$PROJECT_ROOT/logs/validate"
ARCHIVE=""
REPORT=false
JSON=false
RD_STAGE1=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --report) REPORT=true; shift ;;
    --json) JSON=true; shift ;;
    --rd-stage1) RD_STAGE1=true; shift ;;
    -*) hellenia_log "ERROR: opción desconocida: $1"; exit 1 ;;
    *)
      if [[ -z "$ARCHIVE" ]]; then
        ARCHIVE="$1"
      else
        hellenia_log "ERROR: argumento extra: $1"
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$ARCHIVE" ]]; then
  ARCHIVE=$(find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' \) -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
fi

[[ -f "$ARCHIVE" ]] || { hellenia_log "ERROR: Archivo no encontrado: ${ARCHIVE:-<vacío>}"; exit 1; }
[[ -f "$VALIDATOR" ]] || { hellenia_log "ERROR: validador no encontrado: $VALIDATOR"; exit 1; }

hellenia_log "Validando: $ARCHIVE"

ARGS=( "$VALIDATOR" "$ARCHIVE" --version 19.0 )
if $JSON; then
  ARGS+=( --json )
fi
if $RD_STAGE1; then
  ARGS+=( --rd-stage1 )
fi

if $JSON; then
  OUT=$(python3 "${ARGS[@]}")
  echo "$OUT"
  if echo "$OUT" | python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin).get('ok') else 1)"; then
    exit 0
  fi
  exit 1
fi

if ! python3 "${ARGS[@]}"; then
  hellenia_log "FAIL validación Enterprise"
  exit 1
fi

if $REPORT; then
  mkdir -p "$REPORT_DIR"
  STAMP=$(date +%Y-%m-%d_%H%M%S)
  BASENAME=$(basename "$ARCHIVE")
  REPORT_FILE="$REPORT_DIR/enterprise-${STAMP}-$(echo "$BASENAME" | tr -c 'A-Za-z0-9._-' '_').json"
  REPORT_ARGS=( "$VALIDATOR" "$ARCHIVE" --version 19.0 --json )
  if $RD_STAGE1; then
    REPORT_ARGS+=( --rd-stage1 )
  fi
  python3 "${REPORT_ARGS[@]}" > "$REPORT_FILE"
  hellenia_log "Reporte JSON: $REPORT_FILE"
fi

hellenia_log "OK  archivo listo para extract-enterprise-portal.sh (tras aprobación E1a)"
