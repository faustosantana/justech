#!/usr/bin/env bash
# Hotfix 25B.8 — Deploy método get_jt_document_type_short_display + validación TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase25b8-hotfix-doc-type"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/justech_report_design.tgz \
  "${SCRIPT_DIR}/phase25b8-hotfix-doc-type-test.py" root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia
rm -rf custom/justech_report_design
tar xzf /tmp/justech_report_design.tgz -C custom
chmod -R a+rX custom/justech_report_design

# Verificar que el método está en disco
grep -q "get_jt_document_type_short_display" custom/justech_report_design/models/account_move.py \
  || { echo "FAIL: método no está en disco"; exit 1; }

source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env restart odoo
sleep 10

docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase25b8-hotfix-doc-type-test.py > /tmp/out-25b8-hotfix.txt 2>&1
tail -30 /tmp/out-25b8-hotfix.txt

EVIDENCE=/opt/odoo-projects/hellenia/evidence/phase25b8-hotfix-doc-type
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-test-odoo-1:/tmp/phase25b8-hotfix-doc-type/. "$EVIDENCE/"
cp /tmp/out-25b8-hotfix.txt "$EVIDENCE/shell.log"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase25b8-hotfix-doc-type/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done

echo "Evidence: $EVIDENCE_DIR"
ls -la "$EVIDENCE_DIR"
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null || cat "$EVIDENCE_DIR/shell.log" 2>/dev/null | tail -20
