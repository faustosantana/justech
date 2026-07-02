#!/usr/bin/env bash
# Fase 27 — Fix vista previa / imprimir factura PROD
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase27-invoice-preview-print-fix"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/phase27_modules.tgz -C custom hellenia_reports justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase27_modules.tgz \
  "${SCRIPT_DIR}/phase27-invoice-preview-print-fix.py" \
  "${SCRIPT_DIR}/phase27-invoice-preview-print-diagnosis.py" \
  root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
cd "$PROJECT"
source config/production/.env
TS=$(date +%Y-%m-%d_%H%M%S)
BACKUP_DIR="${PROJECT}/backups/hellenia-prod/${TS}"
mkdir -p "$BACKUP_DIR"

echo "=== BACKUP PRODUCCIÓN ${TS} ==="
docker exec hellenia-prod-db-1 pg_dumpall -U "${DB_USER}" | gzip > "${BACKUP_DIR}/postgres_all.sql.gz"
gzip -t "${BACKUP_DIR}/postgres_all.sql.gz"
docker run --rm -v hellenia-prod_odoo-data:/data:ro -v "${BACKUP_DIR}":/backup alpine \
  tar czf /backup/filestore.tar.gz -C /data .
tar czf "${BACKUP_DIR}/custom.tar.gz" -C "$PROJECT" custom
cp docker/production/docker-compose.yml "${BACKUP_DIR}/"
cp config/production/.env "${BACKUP_DIR}/"
echo "timestamp=${TS}" > "${BACKUP_DIR}/MANIFEST.txt"
echo "BACKUP_OK: ${BACKUP_DIR}"

# Diagnóstico ANTES (si módulos viejos)
cd docker/production
docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase27-invoice-preview-print-diagnosis.py > /tmp/out-phase27-before.txt 2>&1 || true
cp /tmp/out-phase27-before.txt "${PROJECT}/evidence/phase27-invoice-preview-print-fix/diagnosis-before.log"

# Desplegar
cd "$PROJECT"
tar xzf /tmp/phase27_modules.tgz -C custom
grep -q "hellenia_legal_notice" custom/hellenia_reports/models/base_document_layout.py
grep -q "report_justech_invoice_wizard_iframe" custom/justech_report_design/report/invoice/justech_invoice_preview.xml

cd docker/production
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u hellenia_reports,justech_report_design --stop-after-init --no-http
docker compose --env-file ../../config/production/.env up -d odoo
sleep 12

docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase27-invoice-preview-print-fix.py > /tmp/out-phase27-after.txt 2>&1
tail -20 /tmp/out-phase27-after.txt

EVIDENCE="${PROJECT}/evidence/phase27-invoice-preview-print-fix"
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-prod-odoo-1:/tmp/phase27-invoice-preview-print-fix/. "$EVIDENCE/" 2>/dev/null || true
docker cp hellenia-prod-odoo-1:/tmp/phase27-invoice-preview-print/diagnosis.json "$EVIDENCE/diagnosis-before.json" 2>/dev/null || true
cp /tmp/out-phase27-after.txt "$EVIDENCE/validation-shell.log"
echo "${BACKUP_DIR}" > "$EVIDENCE/backup_path.txt"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase27-invoice-preview-print-fix/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

echo "=== RESULTADO ==="
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null || tail -30 "$EVIDENCE_DIR/validation-shell.log"
echo "Backup: $(cat "$EVIDENCE_DIR/backup_path.txt" 2>/dev/null)"
