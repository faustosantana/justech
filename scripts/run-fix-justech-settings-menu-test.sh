#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-justech-settings-menu-test"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== Fix Justech Settings Menu TEST ==="
for mod in justech_modules justech_admin; do
  rsync -avz --delete -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
ssh -i "$SSH_KEY" "$VPS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/test/.env
cd /opt/odoo-projects/hellenia/docker/test
docker compose --env-file ../../config/test/.env stop odoo
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -5
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_admin --test-enable --stop-after-init 2>&1 | tee /tmp/justech-settings-test.log | tail -8
grep "tests.result" /tmp/justech-settings-test.log || true
docker compose --env-file ../../config/test/.env up -d odoo
sleep 15
/opt/odoo-projects/hellenia/scripts/healthcheck.sh test 2>&1 | tee /tmp/justech-settings-hc-test.log | tail -8
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/justech-settings-test.log" "$VPS:/tmp/justech-settings-hc-test.log" "$EVIDENCE/" 2>/dev/null || true
cat > "$EVIDENCE/validation.json" <<EOF
{
  "phase": "fix-justech-settings-menu",
  "environment": "test",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "modules": {"justech_modules": "19.0.1.7.2", "justech_admin": "19.0.2.2.0"},
  "menu_path": "Configuración → Justech → Módulos del Cliente"
}
EOF
echo "Evidence: $EVIDENCE"
