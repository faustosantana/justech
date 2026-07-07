#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/purchase-ux-1-test"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== PURCHASE-UX-1 TEST ==="
rsync -avz -e "ssh -i $SSH_KEY" \
  "$PROJECT_ROOT/custom/justech_report_design/" \
  "$VPS:$REMOTE/custom/justech_report_design/"
scp -i "$SSH_KEY" "$SCRIPT_DIR/purchase-ux-1-validate-test.py" "$VPS:/tmp/"
ssh -i "$SSH_KEY" "$VPS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/test/.env
cd /opt/odoo-projects/hellenia/docker/test
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init 2>&1 | tail -6
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --test-tags /justech_report_design:TestPurchaseReportUx --stop-after-init 2>&1 \
  | tee /tmp/purchase-ux1-tests.log | tail -10 || true
docker compose --env-file ../../config/test/.env restart odoo
sleep 12
docker compose --env-file ../../config/test/.env run --rm \
  -e PURCHASE_UX1_EVIDENCE=/var/lib/odoo/purchase-ux-1-validation.json \
  -e PURCHASE_UX1_PDF_DIR=/var/lib/odoo/purchase-ux-1-pdfs \
  odoo odoo shell \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/purchase-ux-1-validate-test.py 2>&1 | tail -35
docker compose --env-file ../../config/test/.env run --rm odoo \
  cat /var/lib/odoo/purchase-ux-1-validation.json > /tmp/purchase-ux1-validation.json
/opt/odoo-projects/hellenia/scripts/healthcheck.sh test 2>&1 | tee /tmp/purchase-ux1-hc.log | tail -8
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/purchase-ux1-validation.json" "$EVIDENCE/validation.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/purchase-ux1-tests.log" "$EVIDENCE/tests.log" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/purchase-ux1-hc.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true
grep -q '"status": "PASS"' "$EVIDENCE/validation.json" && grep -q 'RESULTADO: PASS' "$EVIDENCE/healthcheck.log" && echo "TEST PASS" || echo "TEST FAIL"
