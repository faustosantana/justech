#!/usr/bin/env bash
# Healthcheck completo — Docker, PostgreSQL, Odoo, Traefik, HTTPS, assets, WS, fiscal
# Uso: healthcheck-full.sh [dev|test|prod]
# Salida: PASS / FAIL + JSON en evidence/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ENV_NAME="${1:?Uso: healthcheck-full.sh dev|test|prod}"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_DIR="$(hellenia_env_dir "$ENV_NAME")"
ENV_FILE="$PROJECT_ROOT/config/${ENV_DIR}/.env"
TS=$(date +%Y-%m-%d_%H%M)
REPORT_JSON="$PROJECT_ROOT/evidence/healthcheck-${ENV_NAME}-${TS}.json"
LOG_FILE="$PROJECT_ROOT/logs/deploy/healthcheck-full-${ENV_NAME}-${TS}.log"
FAIL=0
CHECKS=()

mkdir -p "$(dirname "$REPORT_JSON")" "$(dirname "$LOG_FILE")"
hellenia_load_env "$ENV_FILE"

PROJECT="${COMPOSE_PROJECT_NAME}"
ODOO_CONTAINER="$(hellenia_container "$PROJECT" odoo)"
DB_CONTAINER="$(hellenia_container "$PROJECT" db)"
BASE_URL="https://${ODOO_PUBLIC_HOST}"

log() { hellenia_log "$*" | tee -a "$LOG_FILE"; }

record() {
  local name="$1" status="$2" detail="${3:-}"
  CHECKS+=("{\"name\":\"$name\",\"status\":\"$status\",\"detail\":\"$detail\"}")
  if [[ "$status" == "FAIL" ]]; then FAIL=1; fi
  log "[$status] $name${detail:+ — $detail}"
}

log "=== Healthcheck completo: $ENV_NAME ($BASE_URL) ==="

# --- Docker ---
if hellenia_container_running "$ODOO_CONTAINER"; then
  record "docker_odoo" "PASS" "$ODOO_CONTAINER"
else
  record "docker_odoo" "FAIL" "$ODOO_CONTAINER no running"
fi

if hellenia_container_running "$DB_CONTAINER"; then
  record "docker_postgres" "PASS" "$DB_CONTAINER"
else
  record "docker_postgres" "FAIL" "$DB_CONTAINER no running"
fi

# --- PostgreSQL ---
if hellenia_container_running "$DB_CONTAINER"; then
  if docker exec "$DB_CONTAINER" pg_isready -U "${DB_USER}" -d postgres >/dev/null 2>&1; then
    record "postgresql_ready" "PASS"
    db_exists=$(docker exec "$DB_CONTAINER" psql -U "${DB_USER}" -d postgres -tAc \
      "SELECT 1 FROM pg_database WHERE datname='${ODOO_DB_NAME}'" 2>/dev/null | tr -d '[:space:]' || echo "")
    if [[ "$db_exists" == "1" ]]; then
      record "postgresql_database" "PASS" "$ODOO_DB_NAME"
    else
      record "postgresql_database" "FAIL" "BD ${ODOO_DB_NAME} no existe"
    fi
  else
    record "postgresql_ready" "FAIL"
  fi
fi

# --- Odoo container health ---
if hellenia_container_running "$ODOO_CONTAINER"; then
  hc=$(docker inspect --format '{{.State.Health.Status}}' "$ODOO_CONTAINER" 2>/dev/null || echo "unknown")
  if [[ "$hc" == "healthy" ]]; then
    record "odoo_healthcheck" "PASS" "$hc"
  else
    record "odoo_healthcheck" "FAIL" "$hc"
  fi
  if docker exec "$ODOO_CONTAINER" curl -sf http://127.0.0.1:8069/web/login >/dev/null 2>&1; then
    record "odoo_internal_http" "PASS" ":8069/web/login"
  else
    record "odoo_internal_http" "FAIL"
  fi
  if docker exec "$ODOO_CONTAINER" curl -sf http://127.0.0.1:8072/longpolling/poll >/dev/null 2>&1 \
    || docker exec "$ODOO_CONTAINER" bash -c 'echo > /dev/tcp/127.0.0.1/8072' 2>/dev/null; then
    record "odoo_websocket_port" "PASS" ":8072"
  else
    record "odoo_websocket_port" "FAIL" "gevent_port 8072 no responde"
  fi
fi

# --- Traefik ---
if hellenia_container_running "traefik-traefik-1"; then
  record "traefik_container" "PASS"
  if docker logs traefik-traefik-1 2>&1 | tail -200 | grep -q "cannot be linked automatically"; then
    record "traefik_router_link" "FAIL" "router sin service explícito"
  else
    record "traefik_router_link" "PASS"
  fi
  # Verificar que el router del proyecto está registrado
  if docker logs traefik-traefik-1 2>&1 | tail -500 | grep -qE "(${PROJECT}|${ODOO_PUBLIC_HOST})"; then
    record "traefik_router_registered" "PASS" "$PROJECT"
  else
    record "traefik_router_registered" "WARN" "sin mención reciente en logs"
  fi
else
  record "traefik_container" "FAIL" "traefik-traefik-1 no running"
fi

# --- HTTPS ---
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "${BASE_URL}/web/login" 2>/dev/null || echo "000")
if [[ "$code" == "200" ]]; then
  record "https_login" "PASS" "HTTP $code"
else
  record "https_login" "FAIL" "HTTP $code"
fi

# --- TLS cert ---
if curl -sS --max-time 15 -o /dev/null "${BASE_URL}/web/login" 2>/dev/null; then
  record "https_tls" "PASS"
else
  record "https_tls" "FAIL"
fi

# --- Assets (web static) ---
assets_code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
  "${BASE_URL}/web/static/src/libs/fontawesome/css/font-awesome.css" 2>/dev/null || echo "000")
if [[ "$assets_code" == "200" ]]; then
  record "assets_static" "PASS" "HTTP $assets_code"
else
  record "assets_static" "FAIL" "HTTP $assets_code"
fi

# --- WebSocket route (Traefik) ---
ws_code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  "${BASE_URL}/websocket" 2>/dev/null || echo "000")
if [[ "$ws_code" =~ ^(101|400|426|403|200)$ ]]; then
  record "websocket_route" "PASS" "HTTP $ws_code"
else
  record "websocket_route" "FAIL" "HTTP $ws_code (posible 404 Traefik)"
fi

# --- Odoo interno: módulos, NCF, DGII, PDF ---
db_exists="${db_exists:-}"
if hellenia_container_running "$ODOO_CONTAINER" && [[ "${db_exists:-}" == "1" ]]; then
  ODOO_OUT="$PROJECT_ROOT/evidence/healthcheck-${ENV_NAME}-${TS}-odoo.json"
  if docker exec -i "$ODOO_CONTAINER" odoo shell -d "${ODOO_DB_NAME}" --no-http \
    < "${SCRIPT_DIR}/lib/healthcheck-odoo.py" >"$ODOO_OUT" 2>>"$LOG_FILE"; then
    if python3 -c "import json; d=json.load(open('$ODOO_OUT')); exit(0 if d.get('ok') else 1)" 2>/dev/null; then
      record "odoo_fiscal_modules" "PASS" "$(basename "$ODOO_OUT")"
    else
      record "odoo_fiscal_modules" "FAIL" "$(basename "$ODOO_OUT")"
    fi
  else
    record "odoo_fiscal_modules" "FAIL" "healthcheck-odoo.py"
  fi
fi

# --- Resultado ---
RESULT="PASS"
[[ "$FAIL" -eq 0 ]] || RESULT="FAIL"

checks_json=$(IFS=,; echo "[${CHECKS[*]}]")
cat > "$REPORT_JSON" << EOF
{
  "phase": "13.8",
  "environment": "${ENV_NAME}",
  "url": "${BASE_URL}",
  "timestamp": "${TS}",
  "result": "${RESULT}",
  "checks": ${checks_json}
}
EOF

log "=== RESULTADO: ${RESULT} ==="
log "Reporte: $REPORT_JSON"

[[ "$FAIL" -eq 0 ]]
