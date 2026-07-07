#!/usr/bin/env bash
# F31.5 Control Center redesign — deploy TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/f31-5-control-center-redesign-test"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== F31.5 Control Center TEST ==="
for mod in justech_modules justech_admin hellenia_governance; do
  rsync -avz --delete -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
    "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$VPS" bash <<'REMOTE'
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
source "$PROJECT/config/test/.env"
cd "$PROJECT/docker/test"
docker compose --env-file ../../config/test/.env stop odoo
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin,hellenia_governance --stop-after-init 2>&1 | tee /tmp/f315-upgrade.log
docker compose --env-file ../../config/test/.env up -d odoo
sleep 12
docker compose --env-file ../../config/test/.env stop odoo
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --test-enable --stop-after-init \
  --test-tags=/justech_modules 2>&1 | tee /tmp/f315-tests-modules.log | tail -5
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_admin --test-enable --stop-after-init 2>&1 | tee /tmp/f315-tests-admin.log | tail -5
docker compose --env-file ../../config/test/.env up -d odoo
sleep 12
/opt/odoo-projects/hellenia/scripts/healthcheck.sh test 2>&1 | tee /tmp/f315-healthcheck.log | tail -5
REMOTE
echo "Evidence: $EVIDENCE"