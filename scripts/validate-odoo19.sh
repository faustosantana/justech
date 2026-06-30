#!/usr/bin/env bash
# Validaciones post-migración Odoo 19 — DEV o TEST
# Uso: validate-odoo19.sh dev|test
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET="${1:-}"
EXPECTED_VERSION="19.0-20260619"
EXPECTED_SERIE="19.0"
FAIL=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
pass() { log "OK  $*"; }
fail() { log "FAIL $*"; FAIL=1; }

usage() {
  echo "Uso: $0 dev|test"
  exit 1
}

[[ "$TARGET" == "dev" || "$TARGET" == "test" ]] || usage

CONTAINER="hellenia-${TARGET}-odoo-1"
DB_CONTAINER="hellenia-${TARGET}-db-1"

if [[ "$TARGET" == "dev" ]]; then
  URL="https://dev.hellenia.cloud"
else
  URL="https://test.hellenia.cloud"
fi

log "=== Validación Odoo 19 — $TARGET ==="

# 1. Contenedores
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  pass "contenedor $CONTAINER running"
else
  fail "contenedor $CONTAINER no running"
fi

if docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
  pass "contenedor $DB_CONTAINER running"
else
  fail "contenedor $DB_CONTAINER no running"
fi

# 2. Imagen Docker
IMG=$(docker inspect "$CONTAINER" --format '{{.Config.Image}}' 2>/dev/null || echo "n/a")
if [[ "$IMG" == "odoo:19.0-20260619" ]]; then
  pass "imagen Docker: $IMG"
else
  fail "imagen Docker: $IMG (esperado odoo:19.0-20260619)"
fi

# 3. Versión Odoo vía API
VERSION_JSON=$(curl -sS --max-time 15 -X POST "${URL}/web/webclient/version_info" \
  -H 'Content-Type: application/json' -d '{}' 2>/dev/null || echo '{}')
SERVER_VERSION=$(echo "$VERSION_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('server_version',''))" 2>/dev/null || echo "")
SERVER_SERIE=$(echo "$VERSION_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('server_serie',''))" 2>/dev/null || echo "")

if [[ "$SERVER_VERSION" == "$EXPECTED_VERSION" ]]; then
  pass "server_version: $SERVER_VERSION"
elif [[ "$SERVER_SERIE" == "$EXPECTED_SERIE" ]]; then
  pass "server_serie: $SERVER_SERIE (version patch: $SERVER_VERSION)"
else
  fail "server_version: $SERVER_VERSION (esperado $EXPECTED_VERSION)"
fi

# 4. HTTP login
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "${URL}/web/login" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  pass "HTTP /web/login: $HTTP_CODE"
else
  fail "HTTP /web/login: $HTTP_CODE"
fi

# 5. SSL certificado
CERT_SUBJ=$(echo | openssl s_client -connect "${URL#https://}:443" -servername "${URL#https://}" 2>/dev/null \
  | openssl x509 -noout -subject 2>/dev/null || echo "DEFAULT")
if echo "$CERT_SUBJ" | grep -q "${URL#https://}"; then
  pass "SSL cert: $CERT_SUBJ"
else
  fail "SSL cert no válido para ${URL#https://}: $CERT_SUBJ"
fi

# 6. Tracebacks en logs (solo desde último reinicio)
if docker logs "$CONTAINER" --since 10m 2>&1 | grep -qi "traceback"; then
  fail "tracebacks detectados en logs recientes de $CONTAINER"
else
  pass "sin tracebacks recientes en logs"
fi

# 7. l10n_do presente en imagen
if docker exec "$CONTAINER" test -f /usr/lib/python3/dist-packages/odoo/addons/l10n_do/__manifest__.py 2>/dev/null; then
  L10N_VER=$(docker exec "$CONTAINER" python3 -c \
    "import ast; m=ast.literal_eval(open('/usr/lib/python3/dist-packages/odoo/addons/l10n_do/__manifest__.py').read()); print(m.get('version',''))" 2>/dev/null || echo "?")
  pass "l10n_do presente (version $L10N_VER)"
else
  fail "l10n_do no encontrado en imagen"
fi

# 8. l10n_do_edi NO debe estar en Community
if docker exec "$CONTAINER" test -d /usr/lib/python3/dist-packages/odoo/addons/l10n_do_edi 2>/dev/null; then
  log "INFO l10n_do_edi presente (Enterprise)"
else
  pass "l10n_do_edi ausente (esperado en Community)"
fi

# 9. Producción intacta
if docker ps --format '{{.Names}}' | grep -qx "odoo-pecv-odoo-1"; then
  pass "producción odoo-pecv running (sin cambios)"
else
  fail "producción odoo-pecv no detectada"
fi

PROD_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
  "https://odoo-pecv.srv1784296.hstgr.cloud/" 2>/dev/null || echo "000")
if [[ "$PROD_CODE" =~ ^(200|301|302|303)$ ]]; then
  pass "producción HTTP: $PROD_CODE"
else
  fail "producción HTTP: $PROD_CODE"
fi

if [[ "$FAIL" -eq 0 ]]; then
  log "RESULTADO: OK — $TARGET estable en Odoo 19"
else
  log "RESULTADO: FALLOS — revisar arriba"
  exit 1
fi
