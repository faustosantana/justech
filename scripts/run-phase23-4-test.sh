#!/usr/bin/env bash
# Fase 23.4 — Réplica cotización Hellenia — TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase23-4-quote-template-rebuild"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/hellenia_reports.tgz -C custom hellenia_reports
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/hellenia_reports.tgz \
  "${SCRIPT_DIR}/phase23-4-quote-rebuild-test.py" root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia
rm -rf custom/hellenia_reports && tar xzf /tmp/hellenia_reports.tgz -C custom
source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u hellenia_reports --stop-after-init --no-http 2>&1 | tail -5
docker compose --env-file ../../config/test/.env up -d --force-recreate odoo
sleep 25
EVIDENCE=/opt/odoo-projects/hellenia/evidence/phase23-4-quote-template-rebuild
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase23-4-quote-rebuild-test.py > /tmp/out-23.4.txt 2>&1
python3 -c "
import json
d=open('/tmp/out-23.4.txt').read()
m='PHASE23_4:'
r=json.loads(d[d.find(m)+len(m):].strip())
open('$EVIDENCE/validation.json','w').write(json.dumps(r,indent=2,ensure_ascii=False))
print('PASS', r.get('pass'), 'failed', len(r.get('failed_checks',[])))
"
docker cp hellenia-test-odoo-1:/tmp/phase23-4-quote-rebuild/. "$EVIDENCE/" 2>/dev/null || true
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase23-4-quote-template-rebuild/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

if [ -f "$EVIDENCE_DIR/screenshot_quote_1.png" ]; then
  cp "$EVIDENCE_DIR/screenshot_quote_1.png" "$EVIDENCE_DIR/screenshot_reference_comparison.png"
fi

echo "Evidence: $EVIDENCE_DIR"
