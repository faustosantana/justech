#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/purchase-ux-1-prod"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== PURCHASE-UX-1 PROD ==="
ssh -i "$SSH_KEY" "$VPS" "TS=$TS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
BACKUP="/opt/odoo-projects/hellenia/backups/purchase-ux-1-${TS}.sql.gz"
mkdir -p "$(dirname "$BACKUP")"
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env exec -T db \
  pg_dump -U "$DB_USER" -d hellenia_prod | gzip > "$BACKUP"
echo "BACKUP=$BACKUP"
REMOTE
rsync -avz -e "ssh -i $SSH_KEY" \
  "$PROJECT_ROOT/custom/justech_report_design/" \
  "$VPS:$REMOTE/custom/justech_report_design/"
scp -i "$SSH_KEY" "$SCRIPT_DIR/purchase-ux-1-validate-test.py" "$VPS:/tmp/purchase-ux-1-validate-prod.py"
ssh -i "$SSH_KEY" "$VPS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env run --rm odoo odoo \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init 2>&1 | tail -6
docker compose --env-file ../../config/production/.env restart odoo
sleep 12
docker compose --env-file ../../config/production/.env run --rm \
  -e PURCHASE_UX1_EVIDENCE=/var/lib/odoo/purchase-ux-1-validation-prod.json \
  -e PURCHASE_UX1_PDF_DIR=/var/lib/odoo/purchase-ux-1-pdfs-prod \
  odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/purchase-ux-1-validate-prod.py 2>&1 | tail -25
docker compose --env-file ../../config/production/.env run --rm odoo \
  cat /var/lib/odoo/purchase-ux-1-validation-prod.json > /tmp/purchase-ux1-validation-prod.json
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tee /tmp/purchase-ux1-hc-prod.log | tail -8
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/purchase-ux1-validation-prod.json" "$EVIDENCE/validation.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/purchase-ux1-hc-prod.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true
grep -q '"status": "PASS"' "$EVIDENCE/validation.json" && grep -q 'RESULTADO: PASS' "$EVIDENCE/healthcheck.log" && echo "PROD PASS" || echo "PROD FAIL"
