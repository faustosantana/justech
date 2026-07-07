#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-settings-justech-visible-prod"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== Fix Settings Justech Visible PROD ==="
for mod in justech_modules justech_admin; do
  rsync -avz --delete -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" "$SCRIPT_DIR/validate-settings-justech-visible.py" "$VPS:/tmp/"
ssh -i "$SSH_KEY" "$VPS" bash <<REMOTE
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
BACKUP="\$PROJECT/backups/hellenia-prod/settings-justech-visible-${TS}"
mkdir -p "\$BACKUP"
source "\$PROJECT/config/production/.env"
cd "\$PROJECT/docker/production"
docker exec hellenia-prod-db-1 pg_dump -U "\$DB_USER" -Fc hellenia_prod > "\$BACKUP/hellenia_prod.dump"
echo "Backup: \$BACKUP/hellenia_prod.dump"
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm odoo odoo \
  -d hellenia_prod --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -5
docker compose --env-file ../../config/production/.env up -d odoo
sleep 20
docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  --no-http < /tmp/validate-settings-justech-visible.py 2>&1 | tee /tmp/settings-visible-validation-prod.log
docker compose --env-file ../../config/production/.env exec -T odoo cat /var/lib/odoo/settings-justech-visible-validation.json > /tmp/settings-visible-validation-prod.json 2>/dev/null || true
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tail -5
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/settings-visible-validation-prod.json" "$VPS:/tmp/settings-visible-validation-prod.log" "$EVIDENCE/" 2>/dev/null || true
cp "$EVIDENCE/settings-visible-validation-prod.json" "$EVIDENCE/validation.json" 2>/dev/null || true
echo "Evidence: $EVIDENCE"
