#!/usr/bin/env bash
# Fase 13.4 — Hardening producción (solo hellenia_prod)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/config/production/.env"
COMPOSE_DIR="$PROJECT_ROOT/docker/production"
EVIDENCE="$PROJECT_ROOT/evidence/phase13-4-hardening-prod.json"

hellenia_load_env "$ENV_FILE"
cd "$COMPOSE_DIR"

hellenia_log "Fase 13.4 — Hardening hellenia_prod"

# 1. Aplicar gevent_port en odoo.conf si aún dice longpolling_port
CONF="$PROJECT_ROOT/config/production/odoo.conf"
if [[ -f "$CONF" ]] && grep -q '^longpolling_port' "$CONF"; then
  sed -i 's/^longpolling_port/gevent_port/' "$CONF"
  hellenia_log "odoo.conf: longpolling_port → gevent_port"
fi

# 2. Recrear Odoo para aplicar labels Traefik websocket
docker compose --env-file "$ENV_FILE" up -d odoo
sleep 5

# 3. Ejecutar hardening en BD
TMP=$(mktemp)
set +e
docker compose --env-file "$ENV_FILE" run --rm -T odoo odoo shell \
  -d "${ODOO_DB_NAME}" --db_host=db --db_user="${DB_USER}" --db_password="$DB_PASSWORD" --no-http \
  < "${SCRIPT_DIR}/phase13-4-harden-prod.py" > "$TMP" 2>&1
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
  hellenia_log "ERROR shell exit $RC"
  tail -40 "$TMP"
  rm -f "$TMP"
  exit $RC
fi

mkdir -p "$(dirname "$EVIDENCE")"
python3 -c "
import sys
d=open('$TMP').read()
m='PHASE13_4_HARDENING:'
i=d.find(m)
if i<0:
    print(d[-8000:], file=sys.stderr); sys.exit(1)
open('$EVIDENCE','w').write(d[i+len(m):].strip())
print('OK → $EVIDENCE')
"
tail -8 "$TMP"
rm -f "$TMP"

# 4. Verificar websocket en logs recientes
sleep 3
WS_ERR=$(docker logs hellenia-prod-odoo-1 --since 2m 2>&1 | grep -c "Couldn't bind the websocket" || true)
hellenia_log "Errores websocket últimos 2m: $WS_ERR"

hellenia_log "Hardening completado"
