#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-client-module-actions-test"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== FIX client module actions TEST ==="
for mod in justech_modules justech_admin; do
  rsync -avz -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" \
  "$SCRIPT_DIR/fix-client-module-actions-validate.py" \
  "$VPS:/tmp/fix-client-module-actions-validate.py"
ssh -i "$SSH_KEY" "$VPS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/test/.env
cd /opt/odoo-projects/hellenia/docker/test
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -6
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --test-tags /justech_admin --stop-after-init 2>&1 \
  | tee /tmp/fix-cma-tests.log | tail -15 || true
docker compose --env-file ../../config/test/.env restart odoo
sleep 12
docker compose --env-file ../../config/test/.env run --rm \
  -e FIX_CLIENT_MODULE_ACTIONS_EVIDENCE=/var/lib/odoo/fix-client-module-actions-validation.json \
  odoo odoo shell \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/fix-client-module-actions-validate.py 2>&1 | tail -40
docker compose --env-file ../../config/test/.env run --rm odoo \
  cat /var/lib/odoo/fix-client-module-actions-validation.json > /tmp/fix-cma-validation.json
/opt/odoo-projects/hellenia/scripts/healthcheck.sh test 2>&1 | tee /tmp/fix-cma-hc-test.log | tail -10
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/fix-cma-validation.json" "$EVIDENCE/validation.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/fix-cma-tests.log" "$EVIDENCE/tests.log" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:/tmp/fix-cma-hc-test.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true
grep -q '"status": "PASS"' "$EVIDENCE/validation.json" && grep -q 'RESULTADO: PASS' "$EVIDENCE/healthcheck.log" && echo "TEST PASS" || echo "TEST FAIL"
