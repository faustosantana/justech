#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-client-modules-grouping-prod"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
BACKUP="fix-client-modules-grouping-${TS}"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== FIX F31.6 Grouping PROD ==="
for mod in justech_modules justech_admin; do
  rsync -avz --delete -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" "$SCRIPT_DIR/validate-fix-client-modules-grouping.py" "$VPS:/tmp/"
ssh -i "$SSH_KEY" "$VPS" bash <<REMOTE
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
PROJECT=/opt/odoo-projects/hellenia
BACKUP="$PROJECT/backups/hellenia-prod/fix-client-modules-grouping-${TS}"
mkdir -p "$BACKUP"
cd /opt/odoo-projects/hellenia/docker/production
docker exec hellenia-prod-db-1 pg_dump -U "$DB_USER" -Fc hellenia_prod > "$BACKUP/hellenia_prod.dump"
echo "Backup: $BACKUP/hellenia_prod.dump"
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm odoo odoo \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -8
docker compose --env-file ../../config/production/.env up -d odoo
sleep 20
docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/validate-fix-client-modules-grouping.py 2>&1 | tail -30
docker compose --env-file ../../config/production/.env exec -T odoo cat /var/lib/odoo/fix-client-modules-grouping-validation.json > /tmp/grouping-validation-prod.json
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tee /tmp/grouping-hc-prod.log | tail -8
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/grouping-validation-prod.json" "$EVIDENCE/validation.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/grouping-hc-prod.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true
grep -q '"status": "PASS"' "$EVIDENCE/validation.json" && grep -q 'PASS' "$EVIDENCE/healthcheck.log" && echo "PROD PASS" || echo "PROD FAIL"
echo "Backup: ${BACKUP}.dump"
echo "Evidence: $EVIDENCE"
