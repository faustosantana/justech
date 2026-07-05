#!/usr/bin/env bash
# Fase 25 — factura fiscal justech_report_design — TEST only (NO PROD)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase25-invoice-report"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/justech_report_design.tgz \
  "${SCRIPT_DIR}/phase25-invoice-report-test.py" root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia
rm -rf custom/justech_report_design && tar xzf /tmp/justech_report_design.tgz -C custom
source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http 2>&1 | tail -8
docker compose --env-file ../../config/test/.env up -d --force-recreate odoo
sleep 35
EVIDENCE=/opt/odoo-projects/hellenia/evidence/phase25-invoice-report
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase25-invoice-report-test.py > /tmp/out-25.txt 2>&1
tail -30 /tmp/out-25.txt
docker cp hellenia-test-odoo-1:/tmp/phase25-invoice-report/. "$EVIDENCE/" 2>/dev/null || true
cp /tmp/out-25.txt "$EVIDENCE/shell.log" 2>/dev/null || true
for pdf in "$EVIDENCE"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done
ls -la "$EVIDENCE/"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase25-invoice-report/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

echo "Evidence: $EVIDENCE_DIR"
