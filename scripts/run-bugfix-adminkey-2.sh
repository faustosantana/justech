#!/usr/bin/env bash
# BUGFIX-ADMINKEY-2 — Deploy TEST + validate
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/bugfix-adminkey-2"
ENV_NAME="${1:-test}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
LOG="$EVIDENCE/run-${ENV_NAME}-${TS}.log"
exec > >(tee -a "$LOG") 2>&1

if [[ "$ENV_NAME" == "prod" ]]; then
  COMPOSE="docker/production"
  CONFIG="config/production/.env"
  DB="hellenia_prod"
else
  COMPOSE="docker/test"
  CONFIG="config/test/.env"
  DB="hellenia_test"
fi

echo "=== BUGFIX-ADMINKEY-2 $ENV_NAME ==="
for mod in justech_modules justech_admin; do
  rsync -az -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" "$SCRIPT_DIR/bugfix-adminkey-2-validate.py" "$VPS:/tmp/bugfix-adminkey-2-validate.py"

ssh -i "$SSH_KEY" "$VPS" bash -s <<REMOTE
set -euo pipefail
source $REMOTE/$CONFIG
cd $REMOTE/$COMPOSE
docker compose --env-file ../../$CONFIG run --rm odoo odoo \
  -d $DB --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -10
docker compose --env-file ../../$CONFIG restart odoo
sleep 12
docker compose --env-file ../../$CONFIG exec -T \
  -e BUGFIX_ADMINKEY2_EVIDENCE=/tmp/bugfix-adminkey2-validation.json \
  odoo odoo shell \
  -d $DB --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  --no-http < /tmp/bugfix-adminkey-2-validate.py 2>&1 | tee /tmp/bugfix-adminkey2-validate.log | tail -8
test -s /tmp/bugfix-adminkey2-validation.json
/opt/odoo-projects/hellenia/scripts/healthcheck.sh $ENV_NAME 2>&1 | tee /tmp/bugfix-adminkey2-hc.log | tail -6
REMOTE

scp -i "$SSH_KEY" "$VPS:/tmp/bugfix-adminkey2-validation.json" "$EVIDENCE/validation-${ENV_NAME}.json"
scp -i "$SSH_KEY" "$VPS:/tmp/bugfix-adminkey2-hc.log" "$EVIDENCE/healthcheck-${ENV_NAME}.log" 2>/dev/null || true
grep -q '"status": "PASS"' "$EVIDENCE/validation-${ENV_NAME}.json" && grep -q 'RESULTADO: PASS' "$EVIDENCE/healthcheck-${ENV_NAME}.log" && echo "${ENV_NAME^^} PASS" || echo "${ENV_NAME^^} FAIL"
