#!/usr/bin/env bash
# Comparación PDFs A (custom) vs B (Odoo puro) — SOLO TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/report-templates-diagnostic"
mkdir -p "$EVIDENCE_DIR/group_a_custom" "$EVIDENCE_DIR/group_b_pure_odoo" "$EVIDENCE_DIR/backup"

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" \
  "${SCRIPT_DIR}/report-templates-comparison-test.py" \
  root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia/docker/test
source ../../config/test/.env
EVIDENCE=/opt/odoo-projects/hellenia/evidence/report-templates-diagnostic
mkdir -p "$EVIDENCE/group_a_custom" "$EVIDENCE/group_b_pure_odoo" "$EVIDENCE/backup"
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/report-templates-comparison-test.py > /tmp/out-cmp.txt 2>&1
grep REPORT_CMP /tmp/out-cmp.txt || tail -40 /tmp/out-cmp.txt
docker cp hellenia-test-odoo-1:/tmp/report-templates-comparison/. "$EVIDENCE/" 2>/dev/null || true
for pdf in "$EVIDENCE"/group_a_custom/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done
for pdf in "$EVIDENCE"/group_b_pure_odoo/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done
ls -la "$EVIDENCE/group_a_custom/" "$EVIDENCE/group_b_pure_odoo/" 2>/dev/null
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/report-templates-diagnostic/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

echo "Evidence: $EVIDENCE_DIR"
