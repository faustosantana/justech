#!/usr/bin/env bash
# Recibe archivo Enterprise vía Cursor y lo coloca en VPS (sin que el usuario use SCP)
# Uso en VPS:
#   receive-enterprise-archive.sh /tmp/odoo-enterprise.tar.gz
# Uso desde Cursor (sube archivo local al VPS):
#   receive-enterprise-archive.sh --upload /workspace/downloads/enterprise/archivo.tar.gz
#
# Tras recibir: valida automáticamente. NO extrae ni instala sin aprobación E1a.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOWNLOAD_DIR="$PROJECT_ROOT/downloads/enterprise"
DEST="${ENTERPRISE_ARCHIVE_DEST:-$DOWNLOAD_DIR/odoo-19.0-enterprise-sources.tar.gz}"
VPS_HOST="${HELLENIA_VPS_HOST:-2.25.69.179}"
VPS_USER="${HELLENIA_VPS_USER:-root}"

upload_via_scp() {
  local src="$1"
  [[ -f "$src" ]] || { hellenia_log "ERROR: no existe $src"; exit 1; }
  hellenia_log "Subiendo a VPS: $VPS_USER@$VPS_HOST:$DEST"
  install -d -m 700 "$DOWNLOAD_DIR"
  if command -v scp &>/dev/null && [[ -n "${HELLENIA_SSH_KEY:-}" ]]; then
    scp -i "$HELLENIA_SSH_KEY" -o StrictHostKeyChecking=accept-new "$src" "${VPS_USER}@${VPS_HOST}:${DEST}"
  else
    python3 - "$src" "$DEST" "$VPS_HOST" "$VPS_USER" << 'PY'
import os
import sys

import paramiko

src, dest, host, user = sys.argv[1:5]
pw = os.environ.get("HELLENIA_VPS_PASSWORD")
if not pw:
    print("ERROR: definir HELLENIA_VPS_PASSWORD o HELLENIA_SSH_KEY", file=sys.stderr)
    sys.exit(1)
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=pw, timeout=60)
sftp = client.open_sftp()
sftp.put(src, dest)
sftp.chmod(dest, 0o600)
sftp.close()
client.close()
print(f"OK uploaded to {dest}")
PY
  fi
}

if [[ "${1:-}" == "--upload" ]]; then
  upload_via_scp "${2:?Falta ruta archivo local}"
  ARCHIVE="$DEST"
else
  ARCHIVE="${1:-}"
  [[ -n "$ARCHIVE" && -f "$ARCHIVE" ]] || {
    hellenia_log "Uso: $0 <archivo> | $0 --upload <archivo-local>"
    exit 1
  }
  install -d -m 700 "$DOWNLOAD_DIR"
  if [[ "$(realpath "$ARCHIVE")" != "$(realpath "$DEST")" ]]; then
    cp -f "$ARCHIVE" "$DEST"
    chmod 600 "$DEST"
    hellenia_log "Copiado → $DEST"
  fi
  ARCHIVE="$DEST"
fi

hellenia_log "Validando $ARCHIVE ..."
"${SCRIPT_DIR}/validate-enterprise-archive.sh" "$ARCHIVE" --rd-stage1 --report
hellenia_log "Archivo recibido y validado (RD Etapa 1). Pendiente aprobación para upgrade DEV."
