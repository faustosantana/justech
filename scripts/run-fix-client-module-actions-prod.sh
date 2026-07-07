#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-client-module-actions-prod"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== FIX client module actions PROD ==="
ssh -i "$SSH_KEY" "$VPS" "TS=$TS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
BACKUP="/opt/odoo-projects/hellenia/backups/fix-client-module-actions-${TS}.sql.gz"
mkdir -p "$(dirname "$BACKUP")"
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env exec -T db \
  pg_dump -U "$DB_USER" -d hellenia_prod | gzip > "$BACKUP"
echo "BACKUP=$BACKUP"
REMOTE
for mod in justech_modules justech_admin; do
  rsync -avz -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" \
  "$SCRIPT_DIR/fix-client-module-actions-validate.py" \
  "$VPS:/tmp/fix-client-module-actions-validate-prod.py"
ssh -i "$SSH_KEY" "$VPS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env run --rm odoo odoo \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -6
docker compose --env-file ../../config/production/.env restart odoo
sleep 12
docker compose --env-file ../../config/production/.env run --rm \
  -e FIX_CLIENT_MODULE_ACTIONS_EVIDENCE=/var/lib/odoo/fix-client-module-actions-validation-prod.json \
  odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/fix-client-module-actions-validate-prod.py 2>&1 | tail -40
docker compose --env-file ../../config/production/.env run --rm odoo \
  cat /var/lib/odoo/fix-client-module-actions-validation-prod.json > /tmp/fix-cma-validation-prod.json
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tee /tmp/fix-cma-hc-prod.log | tail -10
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/fix-cma-validation-prod.json" "$EVIDENCE/validation.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/fix-cma-hc-prod.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true
grep -q '"status": "PASS"' "$EVIDENCE/validation.json" && grep -q 'RESULTADO: PASS' "$EVIDENCE/healthcheck.log" && echo "PROD PASS" || echo "PROD FAIL"
