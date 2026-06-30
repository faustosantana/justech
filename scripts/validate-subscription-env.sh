#!/usr/bin/env bash
# Valida entorno técnico para suscripción Enterprise (E0.5)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT="$PROJECT_ROOT/logs/deploy/subscription-env-$(date +%Y-%m-%d_%H%M).log"
FAIL=0
SUBSCRIPTION_REF="M260616306091776"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$REPORT"; }
pass() { log "OK  $*"; }
fail() { log "FAIL $*"; FAIL=1; }

mkdir -p "$(dirname "$REPORT")"
log "=== E0.5 Validación entorno suscripción Enterprise ==="
log "Referencia: $SUBSCRIPTION_REF"
log "NOTA: usuarios/renovación/tipo licencia → verificar en odoo.com/my/subscriptions"

# DNS services.odoo.com
if getent hosts services.odoo.com >/dev/null 2>&1; then
  pass "DNS services.odoo.com resuelve"
else
  fail "DNS services.odoo.com no resuelve"
fi

# HTTP saliente puerto 80
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 http://services.odoo.com/ 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" =~ ^[2345] ]]; then
  pass "HTTP saliente services.odoo.com ($HTTP_CODE)"
else
  fail "HTTP saliente services.odoo.com ($HTTP_CODE)"
fi

# Estructura arquitectura
for dir in community enterprise custom config credentials; do
  if [[ -d "$PROJECT_ROOT/$dir" ]]; then
    pass "directorio $dir/ existe"
  else
    fail "directorio $dir/ no existe"
  fi
done

# Enterprise clone status
if [[ -f "$PROJECT_ROOT/enterprise/.git/HEAD" ]]; then
  BRANCH=$(git -C "$PROJECT_ROOT/enterprise" branch --show-current 2>/dev/null || echo "?")
  pass "enterprise/ clonado (rama: $BRANCH)"
else
  log "INFO enterprise/ aún no clonado (esperado antes de E1)"
fi

# GitHub credentials template
if [[ -f "$PROJECT_ROOT/config/credentials/github.env" ]]; then
  pass "github.env presente (chmod $(stat -c '%a' "$PROJECT_ROOT/config/credentials/github.env" 2>/dev/null || echo '?'))"
else
  log "INFO github.env no configurado — requerido para E1 clone"
fi

# Producción intacta
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "odoo-pecv-odoo-1"; then
  pass "producción odoo-pecv running"
else
  log "WARN producción odoo-pecv no detectada en este host"
fi

log "--- Checklist portal (manual) ---"
log "  [ ] Tipo: Odoo Enterprise"
log "  [ ] Estado: In Progress"
log "  [ ] Usuarios incluidos: ___"
log "  [ ] Renovación: ___"
log "  [ ] BD vinculada: ninguna"
log "  [ ] GitHub user vinculado"

if [[ "$FAIL" -eq 0 ]]; then
  log "RESULTADO: OK (checks técnicos)"
else
  log "RESULTADO: FALLOS técnicos"
  exit 1
fi
