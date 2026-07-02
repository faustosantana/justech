#!/usr/bin/env bash
# Auditoría del pipeline de despliegue — paridad DEV/TEST/PROD
# Uso: audit-deployment-pipeline.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT="$PROJECT_ROOT/evidence/deployment-pipeline-audit-$(date +%Y-%m-%d_%H%M).json"
FAIL=0
FINDINGS=()

log() { echo "[$(date '+%H:%M:%S')] $*"; }
finding() {
  local sev="$1" msg="$2"
  FINDINGS+=("{\"severity\":\"$sev\",\"message\":\"$msg\"}")
  log "[$sev] $msg"
  if [[ "$sev" == "FAIL" ]]; then FAIL=1; fi
  return 0
}

log "=== Auditoría pipeline despliegue ==="

# --- Traefik labels: misma fuente ---
TRAEFIK_LIB="$PROJECT_ROOT/docker/lib/traefik-odoo.yaml"
for compose in dev test production; do
  f="$PROJECT_ROOT/docker/${compose}/docker-compose.yml"
  if grep -q 'traefik-odoo.yaml' "$f" 2>/dev/null; then
    finding "PASS" "$compose: usa include traefik-odoo.yaml"
  else
    finding "FAIL" "$compose: NO usa include traefik-odoo.yaml"
  fi
done

[[ -f "$TRAEFIK_LIB" ]] || finding "FAIL" "Falta docker/lib/traefik-odoo.yaml"

# Labels obligatorios en lib
for label in \
  "traefik.http.routers.\${COMPOSE_PROJECT_NAME}.service=\${COMPOSE_PROJECT_NAME}" \
  "traefik.http.routers.\${COMPOSE_PROJECT_NAME}.tls=true" \
  "traefik.http.routers.\${COMPOSE_PROJECT_NAME}.middlewares" \
  "traefik.http.routers.\${COMPOSE_PROJECT_NAME}-ws.service=\${COMPOSE_PROJECT_NAME}-ws"; do
  if grep -qF "$(echo "$label" | sed 's/\\//g')" "$TRAEFIK_LIB" 2>/dev/null || grep -q "${label#*routers.}" "$TRAEFIK_LIB"; then
    finding "PASS" "Label presente: ${label%%=*}"
  else
    # flexible match
    key="${label%%=*}"
    key="${key##*.}"
    if grep -q "$key" "$TRAEFIK_LIB"; then
      finding "PASS" "Label presente: $key"
    else
      finding "FAIL" "Label ausente: $label"
    fi
  fi
done

# --- .env.example: ODOO_PUBLIC_HOST ---
for env in dev test production; do
  ef="$PROJECT_ROOT/config/${env}/.env.example"
  if grep -q '^ODOO_PUBLIC_HOST=' "$ef" 2>/dev/null; then
    finding "PASS" "config/${env}/.env.example tiene ODOO_PUBLIC_HOST"
  else
    finding "FAIL" "config/${env}/.env.example sin ODOO_PUBLIC_HOST"
  fi
done

# --- gevent_port en odoo.conf ---
for conf in dev test; do
  cf="$PROJECT_ROOT/config/${conf}/odoo.conf"
  if grep -q '^gevent_port' "$cf" 2>/dev/null; then
    finding "PASS" "config/${conf}/odoo.conf tiene gevent_port"
  else
    finding "WARN" "config/${conf}/odoo.conf sin gevent_port"
  fi
done
if grep -q '^gevent_port' "$PROJECT_ROOT/config/production/odoo.conf.example" 2>/dev/null; then
  finding "PASS" "production/odoo.conf.example tiene gevent_port"
fi

# --- Scripts pipeline ---
for script in \
  deploy-dev.sh deploy-test.sh \
  backup-hellenia-prod.sh restore-hellenia-prod.sh \
  backup-test.sh restore-test.sh \
  healthcheck-full.sh promote-to-production.sh validate-rollback-test.sh; do
  if [[ -f "$SCRIPT_DIR/$script" ]]; then
    finding "PASS" "Script existe: $script"
  else
    finding "FAIL" "Script ausente: $script"
  fi
done

# --- promote-to-production gates ---
if grep -q 'APPROVE_PROMOTION' "$SCRIPT_DIR/promote-to-production.sh" 2>/dev/null \
  && grep -q 'CERTIFIED_COMMIT' "$SCRIPT_DIR/promote-to-production.sh" 2>/dev/null \
  && grep -q 'backup-hellenia-prod' "$SCRIPT_DIR/promote-to-production.sh" 2>/dev/null; then
  finding "PASS" "promote-to-production.sh exige aprobación + commit + backup"
else
  finding "FAIL" "promote-to-production.sh incompleto"
fi

# --- healthcheck-full cobertura ---
for check in traefik_router_link websocket_route odoo_fiscal_modules; do
  if grep -q "$check" "$SCRIPT_DIR/healthcheck-full.sh" 2>/dev/null; then
    finding "PASS" "healthcheck-full incluye: $check"
  else
    finding "FAIL" "healthcheck-full sin: $check"
  fi
done

# --- deploy-hellenia-prod no debe ser vía directa sin gates ---
if grep -q 'promote-to-production' "$SCRIPT_DIR/deploy-hellenia-prod.sh" 2>/dev/null \
  || head -5 "$SCRIPT_DIR/deploy-hellenia-prod.sh" | grep -q 'pre-Go-Live'; then
  finding "WARN" "deploy-hellenia-prod.sh es bootstrap inicial — usar promote-to-production.sh para actualizaciones"
fi

RESULT="PASS"
[[ "$FAIL" -eq 0 ]] || RESULT="FAIL"

findings_json=$(IFS=,; echo "[${FINDINGS[*]}]")
cat > "$REPORT" << EOF
{
  "phase": "13.8",
  "result": "${RESULT}",
  "findings": ${findings_json}
}
EOF

log "=== RESULTADO: $RESULT ==="
log "Reporte: $REPORT"
[[ "$FAIL" -eq 0 ]]
