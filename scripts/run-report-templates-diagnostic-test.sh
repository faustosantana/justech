#!/usr/bin/env bash
# Inventario reportes QWeb estándar vs personalizados — SOLO TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/report-templates-diagnostic"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/justech_report_templates_test.tgz -C custom justech_report_templates_test
tar czf /tmp/hellenia_reports_ref.tgz -C custom hellenia_reports 2>/dev/null || true

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" \
  /tmp/justech_report_templates_test.tgz \
  "${SCRIPT_DIR}/report-templates-diagnostic-test.py" \
  root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia
mkdir -p custom/justech_report_templates_test
rm -rf custom/justech_report_templates_test/*
tar xzf /tmp/justech_report_templates_test.tgz -C custom
source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -i justech_report_templates_test --stop-after-init --no-http 2>&1 | tail -3
docker compose --env-file ../../config/test/.env restart odoo
sleep 25
EVIDENCE=/opt/odoo-projects/hellenia/evidence/report-templates-diagnostic
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/report-templates-diagnostic-test.py > /tmp/out-report-diag.txt 2>&1
python3 -c "
import json
d=open('/tmp/out-report-diag.txt').read()
m='REPORT_TEMPLATES_DIAG:'
if m in d:
    print(d[d.find(m):d.find(m)+500])
else:
    print('ERROR'); print(d[-2000:])
"
docker cp hellenia-test-odoo-1:/tmp/report-templates-diagnostic/. "$EVIDENCE/" 2>/dev/null || true
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/report-templates-diagnostic/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

echo "Evidence: $EVIDENCE_DIR"
