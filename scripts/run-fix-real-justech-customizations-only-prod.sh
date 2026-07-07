#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-real-justech-customizations-only-prod"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
BACKUP="fix-real-justech-customizations-only-${TS}"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== FIX real Justech customizations only PROD ==="
for mod in justech_modules justech_admin; do
  rsync -avz --delete -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" "$SCRIPT_DIR/validate-fix-real-justech-customizations-only.py" "$VPS:/tmp/"
ssh -i "$SSH_KEY" "$VPS" bash <<REMOTE
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env exec -T db pg_dump -U "\$DB_USER" -Fc hellenia_prod > "/opt/odoo-projects/hellenia/backups/${BACKUP}.dump"
echo "Backup: ${BACKUP}.dump"
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm odoo odoo \
  -d hellenia_prod --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -6
docker compose --env-file ../../config/production/.env up -d odoo
sleep 15
docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  --no-http < /tmp/validate-fix-real-justech-customizations-only.py 2>&1 | tail -30
docker compose --env-file ../../config/production/.env exec -T odoo cat /var/lib/odoo/fix-real-justech-customizations-only-validation.json > /tmp/realonly2-prod-validation.json
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tee /tmp/realonly2-hc-prod.log | tail -8
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/realonly2-prod-validation.json" "$EVIDENCE/validation.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/realonly2-hc-prod.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true
echo "Backup: ${BACKUP}.dump"
echo "Evidence: $EVIDENCE"
