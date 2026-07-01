#!/usr/bin/env bash
# Fase 23.3F — Pulido visual premium cotización — TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase23-3f-quotation-premium-polish"
mkdir -p "$EVIDENCE_DIR"
chmod 777 "$EVIDENCE_DIR" 2>/dev/null || true

cd "$PROJECT_ROOT"
tar czf /tmp/hellenia_reports.tgz -C custom hellenia_reports
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/hellenia_reports.tgz \
  "${SCRIPT_DIR}/phase23-3f-quotation-premium-polish-test.py" root@2.25.69.179:/tmp/

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
docker compose --env-file ../../config/test/.env exec -T -u root odoo \
  bash -c "command -v pdftotext >/dev/null || (apt-get update -qq && apt-get install -y -qq poppler-utils)" || true
EVIDENCE=/opt/odoo-projects/hellenia/evidence/phase23-3f-quotation-premium-polish
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
TMP=$(mktemp)
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase23-3f-quotation-premium-polish-test.py > "$TMP" 2>&1
python3 -c "
d=open('$TMP').read(); m='PHASE23_3F:'; i=d.find(m)
open('$EVIDENCE/validation.json','w').write(d[i+len(m):].strip())
import json; r=json.load(open('$EVIDENCE/validation.json'))
print('RESULT:', 'PASS' if r.get('pass') else 'FAIL', 'failed', len(r.get('failed_checks',[])))
"
docker cp hellenia-test-odoo-1:/tmp/phase23-3f-quotation-premium-polish/. "$EVIDENCE/" 2>/dev/null || \
docker cp hellenia-test-odoo-1:/evidence/phase23-3f-quotation-premium-polish/. "$EVIDENCE/" 2>/dev/null || true
ls -la "$EVIDENCE"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase23-3f-quotation-premium-polish/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true
ls -la "$EVIDENCE_DIR"
