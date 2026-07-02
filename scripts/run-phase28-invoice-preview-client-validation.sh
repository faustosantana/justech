#!/usr/bin/env bash
# Fase 28 — Fix validación cliente Vista previa / Imprimir (void_reason required)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase28-invoice-preview-client-validation"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/phase28_hellenia_reports.tgz -C custom hellenia_reports
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase28_hellenia_reports.tgz \
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
tar czf "${BACKUP_DIR}/custom.tar.gz" -C "$PROJECT" custom
echo "timestamp=${TS}" > "${BACKUP_DIR}/MANIFEST.txt"
echo "BACKUP_OK: ${BACKUP_DIR}"

tar xzf /tmp/phase28_hellenia_reports.tgz -C custom
grep -q "account_move_ncf_void_reason_fix" custom/hellenia_reports/views/account_move_ncf_void_reason_fix.xml

cd docker/production
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u hellenia_reports --stop-after-init --no-http
docker compose --env-file ../../config/production/.env up -d odoo
sleep 12

# Verificar vista en DB
docker exec hellenia-prod-db-1 psql -U odoo -d hellenia_prod -tAc \
  "SELECT latest_version FROM ir_module_module WHERE name='hellenia_reports';"
docker exec hellenia-prod-db-1 psql -U odoo -d hellenia_prod -tAc \
  "SELECT count(*) FROM ir_ui_view WHERE name='account.move.form.hellenia.ncf.void.reason.fix';"

EVIDENCE="${PROJECT}/evidence/phase28-invoice-preview-client-validation"
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
echo "${BACKUP_DIR}" > "$EVIDENCE/backup_path.txt"
echo "DEPLOY_OK"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase28-invoice-preview-client-validation/backup_path.txt \
  "$EVIDENCE_DIR/" 2>/dev/null || true

echo "=== DEPLOY FASE 28 COMPLETADO ==="
cat "$EVIDENCE_DIR/backup_path.txt" 2>/dev/null || true
