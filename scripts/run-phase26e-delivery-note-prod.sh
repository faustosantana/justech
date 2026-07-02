#!/usr/bin/env bash
# Fase 26E — Backup PROD + Conduce como registro justech.delivery.note
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase26e-delivery-note-prod"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/phase26e_justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase26e_justech_report_design.tgz \
  "${SCRIPT_DIR}/phase26e-delivery-note-prod.py" \
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
cp config/production/odoo.conf "${BACKUP_DIR}/" 2>/dev/null || true
BACKUP_BYTES=$(du -sb "${BACKUP_DIR}" | awk '{print $1}')
echo "timestamp=${TS}" > "${BACKUP_DIR}/MANIFEST.txt"
echo "phase=26e-delivery-note" >> "${BACKUP_DIR}/MANIFEST.txt"
echo "size_bytes=${BACKUP_BYTES}" >> "${BACKUP_DIR}/MANIFEST.txt"
echo "BACKUP_OK: ${BACKUP_DIR} (${BACKUP_BYTES} bytes)"

rm -rf custom/justech_report_design
tar xzf /tmp/phase26e_justech_report_design.tgz -C custom
chmod -R a+rX custom/justech_report_design
grep -q "19.0.6.0.1" custom/justech_report_design/__manifest__.py

cd docker/production
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http 2>&1 | tee /tmp/phase26e-upgrade.log | tail -18
docker compose --env-file ../../config/production/.env up -d odoo
sleep 16

docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase26e-delivery-note-prod.py > /tmp/out-phase26e-prod.txt 2>&1
tail -20 /tmp/out-phase26e-prod.txt

EVIDENCE="${PROJECT}/evidence/phase26e-delivery-note-prod"
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-prod-odoo-1:/tmp/phase26e-delivery-note-prod/. "$EVIDENCE/" 2>/dev/null || true
cp /tmp/out-phase26e-prod.txt "$EVIDENCE/shell.log"
echo "${BACKUP_DIR}" > "$EVIDENCE/backup_path.txt"
echo "${BACKUP_BYTES}" > "$EVIDENCE/backup_size_bytes.txt"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase26e-delivery-note-prod/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true
for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done
echo "=== RESULTADO ==="
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null | head -45
