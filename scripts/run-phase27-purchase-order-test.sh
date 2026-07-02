#!/usr/bin/env bash
# Fase 27 — Orden de Compra Hellenia (solo TEST, NO producción)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase27-purchase-order"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/phase27_justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase27_justech_report_design.tgz \
  "${SCRIPT_DIR}/phase27-purchase-order-audit.py" \
  "${SCRIPT_DIR}/phase27-purchase-order-validation.py" \
  root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
cd "$PROJECT"
source config/test/.env

tar xzf /tmp/phase27_justech_report_design.tgz -C custom
chmod -R a+rX custom/justech_report_design

cd docker/test
docker compose --env-file ../../config/test/.env stop odoo || true
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http 2>&1 | tail -20
docker compose --env-file ../../config/test/.env up -d odoo
sleep 14

docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase27-purchase-order-audit.py > /tmp/out-po-audit.txt 2>&1

docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase27-purchase-order-validation.py > /tmp/out-po-val.txt 2>&1
tail -5 /tmp/out-po-val.txt

EVIDENCE="${PROJECT}/evidence/phase27-purchase-order"
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-test-odoo-1:/tmp/phase27-purchase-order/. "$EVIDENCE/" 2>/dev/null || true
cp /tmp/out-po-audit.txt /tmp/out-po-val.txt "$EVIDENCE/" 2>/dev/null || true
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase27-purchase-order/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done

mkdir -p "$PROJECT_ROOT/packages/phase27-purchase-order"
(cd "$PROJECT_ROOT/custom" && zip -r "$PROJECT_ROOT/packages/phase27-purchase-order/justech_report_design-v19.0.7.0.0.zip" justech_report_design -x "*.pyc" -x "*__pycache__*")

echo "=== RESULTADO ==="
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null | head -40
