#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-admin-panel-functions-test"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== FIX admin panel functions TEST ==="
for mod in justech_modules justech_admin; do
  rsync -avz --delete -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" "$SCRIPT_DIR/validate-fix-admin-panel-functions.py" "$VPS:/tmp/"
ssh -i "$SSH_KEY" "$VPS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/test/.env
cd /opt/odoo-projects/hellenia/docker/test
docker compose --env-file ../../config/test/.env stop odoo
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -6
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --test-enable --stop-after-init 2>&1 | tee /tmp/adminpanel-tests.log | tail -8 || true
grep "tests.result" /tmp/adminpanel-tests.log || true
docker compose --env-file ../../config/test/.env up -d odoo
sleep 15
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/validate-fix-admin-panel-functions.py 2>&1 | tail -35
docker compose --env-file ../../config/test/.env exec -T odoo cat /var/lib/odoo/fix-admin-panel-functions-validation.json > /tmp/adminpanel-validation.json
/opt/odoo-projects/hellenia/scripts/healthcheck.sh test 2>&1 | tee /tmp/adminpanel-hc-test.log | tail -8
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/adminpanel-validation.json" "$EVIDENCE/validation.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/adminpanel-tests.log" "$EVIDENCE/tests.log" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/adminpanel-hc-test.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true
echo "Evidence: $EVIDENCE"
