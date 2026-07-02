#!/usr/bin/env bash
# Fase 26 — Conduce de Entrega (solo TEST, no producción)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase26-delivery-slip"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/phase26_justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase26_justech_report_design.tgz \
  "${SCRIPT_DIR}/phase26-delivery-slip-audit.py" \
  "${SCRIPT_DIR}/phase26-delivery-slip-validation.py" \
  root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
cd "$PROJECT"
source config/test/.env

tar xzf /tmp/phase26_justech_report_design.tgz -C custom
chmod -R a+rX custom/justech_report_design

cd docker/test
docker compose --env-file ../../config/test/.env stop odoo
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http 2>&1 | tail -15
docker compose --env-file ../../config/test/.env up -d odoo
sleep 12

docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase26-delivery-slip-audit.py > /tmp/out-audit.txt 2>&1 || true

docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase26-delivery-slip-validation.py > /tmp/out-val.txt 2>&1
tail -25 /tmp/out-val.txt

EVIDENCE="${PROJECT}/evidence/phase26-delivery-slip"
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-test-odoo-1:/tmp/phase26-delivery-slip/. "$EVIDENCE/" 2>/dev/null || true
cp /tmp/out-audit.txt /tmp/out-val.txt "$EVIDENCE/" 2>/dev/null || true
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase26-delivery-slip/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

cp /tmp/phase26-delivery-slip-audit.json "$EVIDENCE_DIR/audit.json" 2>/dev/null || true

for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done

# Validación textual en host (pdftotext no está en el contenedor Odoo)
if command -v pdftotext >/dev/null && [ -f "$EVIDENCE_DIR/validation.json" ]; then
  python3 "$SCRIPT_DIR/phase26b-host-pdf-check.py" "$EVIDENCE_DIR" || true
fi

mkdir -p "$PROJECT_ROOT/packages/phase26-delivery-slip"
(cd "$PROJECT_ROOT/custom" && zip -r "$PROJECT_ROOT/packages/phase26-delivery-slip/justech_report_design-v19.0.5.0.0.zip" justech_report_design -x "*.pyc" -x "*__pycache__*")

echo "=== EVIDENCE ==="
ls -la "$EVIDENCE_DIR"
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null | head -40
