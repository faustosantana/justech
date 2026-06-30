#!/usr/bin/env bash
# Healthcheck — producción actual + DEV + TEST
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT="$PROJECT_ROOT/logs/deploy/healthcheck-$(date +%Y-%m-%d_%H%M).log"
FAIL=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$REPORT"; }

mkdir -p "$(dirname "$REPORT")"
log "=== Hellenia Odoo Healthcheck ==="

check_container() {
  local name="$1"
  if docker ps --format '{{.Names}}' | grep -qx "$name"; then
    log "OK  container: $name"
  else
    log "FAIL container: $name (no running)"
    FAIL=1
  fi
}

check_url() {
  local url="$1"
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$url" 2>/dev/null || echo "000")
  if [[ "$code" =~ ^(200|301|302|303)$ ]]; then
    log "OK  url: $url ($code)"
  else
    log "FAIL url: $url ($code)"
    FAIL=1
  fi
}

check_odoo_version() {
  local url="$1"
  local expected_serie="${2:-19.0}"
  local version serie
  version=$(curl -sS --max-time 15 -X POST "${url}/web/webclient/version_info" \
    -H 'Content-Type: application/json' -d '{}' 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('server_version',''))" 2>/dev/null || echo "")
  serie=$(curl -sS --max-time 15 -X POST "${url}/web/webclient/version_info" \
    -H 'Content-Type: application/json' -d '{}' 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('server_serie',''))" 2>/dev/null || echo "")
  if [[ "$serie" == "$expected_serie" ]]; then
    log "OK  odoo version: $version (serie $serie)"
  else
    log "FAIL odoo version: $version (esperado serie $expected_serie)"
    FAIL=1
  fi
}

check_db_separate() {
  local c1="$1" c2="$2"
  local v1 v2
  v1=$(docker exec "$c1" psql -U odoo -d postgres -tAc "SELECT pg_size_pretty(pg_database_size('postgres'));" 2>/dev/null || echo "n/a")
  v2=$(docker exec "$c2" psql -U odoo -d postgres -tAc "SELECT pg_size_pretty(pg_database_size('postgres'));" 2>/dev/null || echo "n/a")
  log "INFO db $c1 postgres size: $v1"
  log "INFO db $c2 postgres size: $v2"
}

log "--- Producción actual (odoo-pecv) ---"
check_container "odoo-pecv-odoo-1"
check_container "odoo-pecv-db-1"
check_url "https://odoo-pecv.srv1784296.hstgr.cloud/"

log "--- DEV ---"
if docker ps --format '{{.Names}}' | grep -q '^hellenia-dev-odoo-1$'; then
  check_container "hellenia-dev-odoo-1"
  check_container "hellenia-dev-db-1"
  check_url "https://dev.hellenia.cloud/"
  check_odoo_version "https://dev.hellenia.cloud" "19.0"
  docker logs hellenia-dev-odoo-1 --tail 5 2>&1 | tee -a "$REPORT"
else
  log "SKIP DEV (no desplegado aún)"
fi

log "--- TEST ---"
if docker ps --format '{{.Names}}' | grep -q '^hellenia-test-odoo-1$'; then
  check_container "hellenia-test-odoo-1"
  check_container "hellenia-test-db-1"
  check_url "https://test.hellenia.cloud/"
  check_odoo_version "https://test.hellenia.cloud" "19.0"
  docker logs hellenia-test-odoo-1 --tail 5 2>&1 | tee -a "$REPORT"
else
  log "SKIP TEST (no desplegado aún)"
fi

log "--- PROD (hellenia-prod) ---"
if docker ps --format '{{.Names}}' | grep -q '^hellenia-prod-odoo-1$'; then
  check_container "hellenia-prod-odoo-1"
  check_container "hellenia-prod-db-1"
  check_url "https://odoo.hellenia.cloud/"
  check_odoo_version "https://odoo.hellenia.cloud" "19.0"
  docker logs hellenia-prod-odoo-1 --tail 5 2>&1 | tee -a "$REPORT"
else
  log "SKIP PROD (no desplegado aún)"
fi

log "--- Traefik ---"
check_container "traefik-traefik-1"

if [[ "$FAIL" -eq 0 ]]; then
  log "RESULTADO: OK"
else
  log "RESULTADO: FALLOS DETECTADOS"
  exit 1
fi
