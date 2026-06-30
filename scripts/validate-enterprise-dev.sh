#!/usr/bin/env bash
# Valida Odoo Enterprise activo en DEV (imagen hellenia-odoo:19-enterprise)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/dev/.env"
FAIL=0
INSTALL_L10N=""
SKIP_LICENSE=false

for arg in "$@"; do
  case "$arg" in
    --l10n) INSTALL_L10N="--l10n" ;;
    --no-license) SKIP_LICENSE=true ;;
  esac
done

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
pass() { log "OK  $*"; }
fail() { log "FAIL $*"; FAIL=1; }

# shellcheck disable=SC1090
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

CONTAINER="hellenia-dev-odoo-1"
DB_CONTAINER="hellenia-dev-db-1"
URL="https://dev.hellenia.cloud"
DB="${ODOO_DB_NAME:-hellenia_dev}"

log "=== Validación Enterprise DEV ==="

# Docker
docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" && pass "contenedor Odoo running" || fail "contenedor Odoo no running"
docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER" && pass "contenedor PostgreSQL running" || fail "PostgreSQL no running"

IMG=$(docker inspect "$CONTAINER" --format '{{.Config.Image}}' 2>/dev/null || echo "?")
echo "$IMG" | grep -q 'hellenia-odoo:19-enterprise' && pass "imagen hellenia-odoo:19-enterprise" || fail "imagen inesperada: $IMG"

# Enterprise horneado (sin volumen)
docker exec "$CONTAINER" test -f /opt/odoo/enterprise/addons/web_enterprise/__manifest__.py \
  && pass "web_enterprise en imagen" || fail "web_enterprise no en imagen"
docker exec "$CONTAINER" test -d /opt/odoo/custom && pass "custom en imagen" || fail "custom no en imagen"

# Sin montaje enterprise legacy
if docker inspect "$CONTAINER" --format '{{json .Mounts}}' | grep -q '/mnt/enterprise'; then
  fail "aún monta volumen /mnt/enterprise (debe estar horneado)"
else
  pass "sin volumen /mnt/enterprise"
fi

# addons_path
AP=$(docker exec "$CONTAINER" grep -E '^addons_path' /etc/odoo/odoo.conf 2>/dev/null || echo "")
log "INFO $AP"
echo "$AP" | grep -q '/opt/odoo/enterprise/addons' && pass "addons_path incluye enterprise en imagen" || fail "addons_path incorrecto"

# web_enterprise instalado en BD
INSTALLED=$(docker exec "$DB_CONTAINER" psql -U odoo -d "$DB" -tAc \
  "SELECT state FROM ir_module_module WHERE name='web_enterprise';" 2>/dev/null || echo "")
if [[ "$INSTALLED" == "installed" ]]; then
  pass "web_enterprise instalado en BD"
else
  fail "web_enterprise estado: ${INSTALLED:-vacío}"
fi

# l10n_do NO instalado (por diseño E1a)
for mod in l10n_do l10n_do_edi l10n_do_reports; do
  STATE=$(docker exec "$DB_CONTAINER" psql -U odoo -d "$DB" -tAc \
    "SELECT COALESCE(state,'absent') FROM ir_module_module WHERE name='$mod';" 2>/dev/null || echo "absent")
  if [[ "$STATE" == "installed" ]]; then
    fail "$mod instalado (no debe en E1a)"
  else
    pass "$mod no instalado ($STATE)"
  fi
done

# HTTP / HTTPS
CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "${URL}/web/login")
[[ "$CODE" == "200" ]] && pass "HTTPS login HTTP $CODE" || fail "HTTPS login HTTP $CODE"

# Traefik
docker ps --format '{{.Names}}' | grep -qx "traefik-traefik-1" && pass "Traefik running" || fail "Traefik no running"

# Logs recientes sin ERROR crítico
ERR_COUNT=$(docker logs "$CONTAINER" --since 5m 2>&1 | grep -cE ' ERROR ' || true)
if [[ "${ERR_COUNT:-0}" -gt 5 ]]; then
  fail "demasiados ERROR en logs Odoo ($ERR_COUNT en 5m)"
else
  pass "logs Odoo sin errores críticos (${ERR_COUNT:-0} ERROR en 5m)"
fi

# Licencia — solo si no se pidió omitir
if ! $SKIP_LICENSE; then
  ENT_CODE=$(docker exec "$DB_CONTAINER" psql -U odoo -d "$DB" -tAc \
    "SELECT value FROM ir_config_parameter WHERE key='database.enterprise_code';" 2>/dev/null || echo "")
  if [[ -n "$ENT_CODE" && "$ENT_CODE" != "" ]]; then
    pass "database.enterprise_code presente"
  else
    log "WARN database.enterprise_code vacío — registrar suscripción en UI"
  fi
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
    STATE=$(docker exec "$DB_CONTAINER" psql -U odoo -d "$DB" -tAc \
      "SELECT state FROM ir_module_module WHERE name='$mod';" 2>/dev/null || echo "")
    [[ "$STATE" == "installed" ]] && pass "$mod instalado" || fail "$mod estado: $STATE"
  done
fi

# Producción
docker ps --format '{{.Names}}' | grep -qx "odoo-pecv-odoo-1" && pass "producción intacta" || log "WARN prod no en host"

if [[ "$FAIL" -eq 0 ]]; then
  log "RESULTADO: OK"
else
  log "RESULTADO: FALLOS"
  exit 1
fi
