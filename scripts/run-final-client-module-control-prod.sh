#!/usr/bin/env bash
# Deploy final client module control to PROD (run only after TEST PASS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/final-client-module-control-prod"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1

echo "=== Final Client Module Control PROD ==="

for mod in justech_modules justech_admin hellenia_governance; do
  rsync -avz --delete -e "ssh -i $SSH_KEY" \
    "$PROJECT_ROOT/custom/${mod}/" \
    "$VPS:$REMOTE/custom/${mod}/"
done

ssh -i "$SSH_KEY" "$VPS" bash <<REMOTE
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
BACKUP="\$PROJECT/backups/hellenia-prod/client-module-control-${TS}"
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
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tee /tmp/client-module-control-healthcheck-prod.log
REMOTE

scp -i "$SSH_KEY" "$VPS:/tmp/client-module-control-healthcheck-prod.log" "$EVIDENCE/" 2>/dev/null || true
HC=$(ssh -i "$SSH_KEY" "$VPS" 'ls -1t /opt/odoo-projects/hellenia/evidence/healthcheck-prod-*.json 2>/dev/null | head -1')
if [[ -n "$HC" ]]; then
  scp -i "$SSH_KEY" "$VPS:$HC" "$EVIDENCE/HEALTHCHECK.json"
fi

cat > "$EVIDENCE/validation.json" <<EOF
{
  "phase": "final-client-module-control",
  "environment": "prod",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "url": "https://odoo.hellenia.cloud",
  "modules": {
    "justech_modules": "19.0.1.7.1",
    "justech_admin": "19.0.2.1.0"
  },
  "backup_pattern": "client-module-control-${TS}",
  "healthcheck_log": "client-module-control-healthcheck-prod.log",
  "prod_touched": true
}
EOF

echo "Evidence: $EVIDENCE"
