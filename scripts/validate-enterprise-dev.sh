#!/usr/bin/env bash
# Valida Odoo Enterprise activo en DEV + opcional localización RD
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/dev/.env"
FAIL=0
INSTALL_L10N="${1:-}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
pass() { log "OK  $*"; }
fail() { log "FAIL $*"; FAIL=1; }

# shellcheck disable=SC1090
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

CONTAINER="hellenia-dev-odoo-1"
URL="https://dev.hellenia.cloud"
DB="${ODOO_DB_NAME:-hellenia_dev}"

log "=== Validación Enterprise DEV ==="

# Contenedor e imagen
docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" && pass "contenedor running" || fail "contenedor no running"

IMG=$(docker inspect "$CONTAINER" --format '{{.Config.Image}}' 2>/dev/null || echo "?")
log "INFO imagen: $IMG"

# Enterprise montado
docker exec "$CONTAINER" test -d /mnt/enterprise/web_enterprise && pass "enterprise montado" || fail "enterprise no montado"
docker exec "$CONTAINER" test -d /mnt/custom && pass "custom montado" || fail "custom no montado"

# addons_path
AP=$(docker exec "$CONTAINER" grep -E '^addons_path' /etc/odoo/odoo.conf 2>/dev/null || echo "")
log "INFO $AP"
echo "$AP" | grep -q '/mnt/enterprise' && pass "addons_path incluye enterprise" || fail "addons_path sin enterprise"

# web_enterprise instalado en BD
INSTALLED=$(docker exec hellenia-dev-db-1 psql -U odoo -d "$DB" -tAc \
  "SELECT state FROM ir_module_module WHERE name='web_enterprise';" 2>/dev/null || echo "")
if [[ "$INSTALLED" == "installed" ]]; then
  pass "web_enterprise instalado en BD"
else
  fail "web_enterprise estado: $INSTALLED"
fi

# HTTP
CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "${URL}/web/login")
[[ "$CODE" == "200" ]] && pass "login HTTP $CODE" || fail "login HTTP $CODE"

# Suscripción registrada (database.enterprise_code)
ENT_CODE=$(docker exec hellenia-dev-db-1 psql -U odoo -d "$DB" -tAc \
  "SELECT value FROM ir_config_parameter WHERE key='database.enterprise_code';" 2>/dev/null || echo "")
if [[ -n "$ENT_CODE" && "$ENT_CODE" != "" ]]; then
  pass "database.enterprise_code presente (suscripción registrada)"
else
  log "WARN database.enterprise_code vacío — registrar M260616306091776 en UI"
fi

# Instalar localización RD si se pasa --l10n
if [[ "$INSTALL_L10N" == "--l10n" ]]; then
  log "--- Instalando l10n_do, l10n_do_edi, l10n_do_reports ---"
  source "$ENV_FILE"
  cd "$PROJECT_ROOT/docker/dev"
  docker compose --env-file "$ENV_FILE" stop odoo
  docker compose --env-file "$ENV_FILE" run --rm odoo odoo \
    -d "$DB" --db_host=db --db_user="${DB_USER:-odoo}" --db_password="$DB_PASSWORD" \
    -i l10n_do,l10n_do_edi,l10n_do_reports --stop-after-init 2>&1 | tail -30
  docker compose --env-file "$ENV_FILE" up -d odoo
  sleep 30

  for mod in l10n_do l10n_do_edi l10n_do_reports; do
    STATE=$(docker exec hellenia-dev-db-1 psql -U odoo -d "$DB" -tAc \
      "SELECT state FROM ir_module_module WHERE name='$mod';" 2>/dev/null || echo "")
    [[ "$STATE" == "installed" ]] && pass "$mod instalado" || fail "$mod estado: $STATE"
  done

  # Verificar impuestos ITBIS
  TAX_COUNT=$(docker exec hellenia-dev-db-1 psql -U odoo -d "$DB" -tAc \
    "SELECT COUNT(*) FROM account_tax WHERE name ILIKE '%ITBIS%';" 2>/dev/null || echo "0")
  log "INFO impuestos ITBIS en BD: $TAX_COUNT"
  [[ "$TAX_COUNT" -gt 0 ]] && pass "impuestos ITBIS configurados" || fail "sin impuestos ITBIS"

  log "INFO eNCF/Infile: NO configurado (por diseño)"
  log "INFO wizard: NO ejecutado"
fi

# Producción
docker ps --format '{{.Names}}' | grep -qx "odoo-pecv-odoo-1" && pass "producción intacta" || log "WARN prod no en host"

if [[ "$FAIL" -eq 0 ]]; then
  log "RESULTADO: OK"
else
  log "RESULTADO: FALLOS"
  exit 1
fi
