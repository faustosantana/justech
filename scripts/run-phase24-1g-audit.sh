#!/usr/bin/env bash
# Fase 24.1G — Auditoría justech_report_design antes de promoción oficial (solo TEST)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase24-1g-audit"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" \
  /tmp/justech_report_design.tgz \
  "${SCRIPT_DIR}/phase24-1g-quotation-audit.py" \
  root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia
rm -rf custom/justech_report_design && tar xzf /tmp/justech_report_design.tgz -C custom
source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http 2>&1 | tail -5
docker compose --env-file ../../config/test/.env up -d --force-recreate odoo
sleep 30
EVIDENCE=/opt/odoo-projects/hellenia/evidence/phase24-1g-audit
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase24-1g-quotation-audit.py > /tmp/out-24.1g.txt 2>&1
python3 -c "
import json
d=open('/tmp/out-24.1g.txt').read()
m='PHASE24_1G:'
if m in d:
    r=json.loads(d[d.find(m)+len(m):].strip())
    open('$EVIDENCE/audit.json','w').write(json.dumps(r,indent=2,ensure_ascii=False))
    print('ready_for_official', r.get('ready_for_official'))
    print('sections', {k:v['status'] for k,v in r.get('sections',{}).items()})
    print('scenario_fails', [k for k,v in r.get('scenarios',{}).items() if v.get('status')=='FAIL'])
else:
    print('FAIL'); print(d[-4000:])
"
docker cp hellenia-test-odoo-1:/tmp/phase24-1g-audit/. "$EVIDENCE/" 2>/dev/null || true
ls -la "$EVIDENCE/"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase24-1g-audit/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

echo "Audit evidence: $EVIDENCE_DIR"
