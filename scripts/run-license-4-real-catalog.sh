#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_NAME="${1:-prod}"
EVIDENCE="$PROJECT_ROOT/evidence/license-4-real-catalog-${ENV_NAME}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1

DB="hellenia_prod"
CFG="production"
BACKUP="/opt/odoo-projects/hellenia/backups/hellenia-prod/license-4-${TS}"
echo "=== LICENSE-4 PROD ==="
ssh -i "$SSH_KEY" "$VPS" "BACKUP='$BACKUP' bash -s" <<REMOTE
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
mkdir -p "\$BACKUP"
docker exec hellenia-prod-db-1 pg_dump -U "\$DB_USER" -Fc hellenia_prod > "\$BACKUP/hellenia_prod.dump"
echo "BACKUP_OK=\$BACKUP"
REMOTE
echo "$BACKUP" > "$EVIDENCE/BACKUP_PATH.txt"

for mod in justech_modules justech_admin; do
  rsync -avz -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" "$SCRIPT_DIR/license-4-real-catalog-validate.py" "$VPS:/tmp/license-4-real-catalog-validate.py"

ssh -i "$SSH_KEY" "$VPS" bash <<REMOTE
set -euo pipefail
source /opt/odoo-projects/hellenia/config/${CFG}/.env
cd /opt/odoo-projects/hellenia/docker/${CFG}
docker compose --env-file ../../config/${CFG}/.env stop odoo
docker compose --env-file ../../config/${CFG}/.env run --rm odoo odoo \
  -d ${DB} --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -12
docker compose --env-file ../../config/${CFG}/.env up -d odoo
sleep 18
docker compose --env-file ../../config/${CFG}/.env exec -T \
  -e LICENSE4_EVIDENCE=/var/lib/odoo/license-4-validation.json \
  odoo odoo shell \
  -d ${DB} --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  --no-http < /tmp/license-4-real-catalog-validate.py 2>&1 | grep LICENSE4:
docker compose --env-file ../../config/${CFG}/.env cp odoo:/var/lib/odoo/license-4-validation.json /tmp/license-4-validation.json 2>/dev/null || true
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tee /tmp/license-4-hc.log | tail -6
REMOTE

scp -i "$SSH_KEY" "$VPS:/tmp/license-4-validation.json" "$EVIDENCE/validation.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/license-4-hc.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true
grep -q '"status": "PASS"' "$EVIDENCE/validation.json" && grep -q 'RESULTADO: PASS' "$EVIDENCE/healthcheck.log" && echo "prod PASS" || echo "prod FAIL"
