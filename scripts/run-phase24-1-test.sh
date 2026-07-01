#!/usr/bin/env bash
# Fase 24.1 — justech_report_design cotización QWeb+SCSS — TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase24-1-report-design"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/justech_report_design.tgz \
  "${SCRIPT_DIR}/phase24-1-report-design-test.py" root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia
rm -rf custom/justech_report_design && tar xzf /tmp/justech_report_design.tgz -C custom
source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -i justech_report_design --stop-after-init --no-http 2>&1 | tail -5
docker compose --env-file ../../config/test/.env up -d --force-recreate odoo
sleep 30
EVIDENCE=/opt/odoo-projects/hellenia/evidence/phase24-1-report-design
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase24-1-report-design-test.py > /tmp/out-24.1.txt 2>&1
python3 -c "
import json
d=open('/tmp/out-24.1.txt').read()
m='PHASE24_1:'
if m in d:
    r=json.loads(d[d.find(m)+len(m):].strip())
    open('$EVIDENCE/validation.json','w').write(json.dumps(r,indent=2,ensure_ascii=False))
    print('PASS', r.get('pass'), 'failed', len(r.get('failed_checks',[])))
else:
    print('FAIL'); print(d[-3000:])
"
docker cp hellenia-test-odoo-1:/tmp/phase24-1-report-design/. "$EVIDENCE/" 2>/dev/null || true
for pdf in "$EVIDENCE"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done
[ -f "$EVIDENCE/screenshot_quote_1.png" ] && cp "$EVIDENCE/screenshot_quote_1.png" "$EVIDENCE/screenshot_reference.png" 2>/dev/null || true
ls -la "$EVIDENCE/"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase24-1-report-design/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

echo "Evidence: $EVIDENCE_DIR"
