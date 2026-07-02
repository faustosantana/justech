#!/usr/bin/env bash
# Fase 25A — Paquete revisión visual factura (solo hellenia_test)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase25-invoice-review"
REVIEW_PKG="$PROJECT_ROOT/packages/phase25-invoice-review"
mkdir -p "$EVIDENCE_DIR" "$REVIEW_PKG"

cd "$PROJECT_ROOT"
tar czf /tmp/justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/justech_report_design.tgz \
  "${SCRIPT_DIR}/phase25a-invoice-visual-review.py" root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia
rm -rf custom/justech_report_design && tar xzf /tmp/justech_report_design.tgz -C custom
source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase25a-invoice-visual-review.py > /tmp/out-25a.txt 2>&1
tail -3 /tmp/out-25a.txt
EVIDENCE=/opt/odoo-projects/hellenia/evidence/phase25-invoice-review
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-test-odoo-1:/tmp/phase25-invoice-review/. "$EVIDENCE/"
cp /tmp/out-25a.txt "$EVIDENCE/shell.log"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase25-invoice-review/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

# PNG en host (pdftoppm no está en contenedor Odoo)
for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done
[ -f "$EVIDENCE_DIR/03_invoice_22_lines.pdf" ] && pdftoppm -f 2 -l 2 -png -singlefile "$EVIDENCE_DIR/03_invoice_22_lines.pdf" "$EVIDENCE_DIR/03_invoice_22_lines_p2" 2>/dev/null || true

# Copiar fuentes al paquete
mkdir -p "$REVIEW_PKG/xml" "$REVIEW_PKG/scss"
cp custom/justech_report_design/report/invoice/justech_invoice_template.xml "$REVIEW_PKG/xml/"
cp custom/justech_report_design/static/src/scss/hellenia_invoice.scss "$REVIEW_PKG/scss/"
cp custom/justech_report_design/static/src/scss/hellenia_quotation.scss "$REVIEW_PKG/scss/"
cp "$EVIDENCE_DIR"/*.pdf "$EVIDENCE_DIR"/*.png "$EVIDENCE_DIR"/*.json "$REVIEW_PKG/" 2>/dev/null || true

echo "Evidence: $EVIDENCE_DIR"
