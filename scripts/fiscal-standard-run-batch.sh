#!/usr/bin/env bash
# Ejecuta validación estándar para varias empresas en secuencia.
set -euo pipefail
SCRIPT_DIR="${SCRIPT_DIR:-/opt/odoo-dev/scripts}"
for SLUG in "$@"; do
  bash "$SCRIPT_DIR/fiscal-standard-run.sh" "$SLUG"
done
