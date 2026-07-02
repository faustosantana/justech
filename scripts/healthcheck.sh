#!/usr/bin/env bash
# Healthcheck — wrapper Fase 13.8 (delega a healthcheck-full.sh)
# Uso: healthcheck.sh [dev|test|prod|all]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_env() {
  local env="$1"
  local container
  case "$env" in
    prod) container="hellenia-prod-odoo-1" ;;
    test) container="hellenia-test-odoo-1" ;;
    dev)  container="hellenia-dev-odoo-1" ;;
    *) echo "Ambiente desconocido: $env"; return 1 ;;
  esac
  if docker ps --format '{{.Names}}' | grep -qx "$container"; then
    "$SCRIPT_DIR/healthcheck-full.sh" "$env"
  else
    echo "[SKIP] $env — contenedor $container no desplegado"
    return 0
  fi
}

TARGET="${1:-all}"

if [[ "$TARGET" == "all" ]]; then
  FAIL=0
  for env in dev test prod; do
    if ! run_env "$env"; then FAIL=1; fi
  done
  [[ "$FAIL" -eq 0 ]]
else
  run_env "$TARGET"
fi
