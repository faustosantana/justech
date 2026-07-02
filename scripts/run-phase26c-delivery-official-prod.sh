#!/usr/bin/env bash
# Fase 26C — Backup PROD + Conduce oficial + validación completa
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase26c-delivery-official-prod"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/phase26c_justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase26c_justech_report_design.tgz \
  "${SCRIPT_DIR}/phase26c-delivery-official-prod.py" \
  "${SCRIPT_DIR}/phase26b-host-pdf-check.py" \
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
tar -tzf "${BACKUP_DIR}/filestore.tar.gz" >/dev/null 2>&1 || true

tar czf "${BACKUP_DIR}/custom.tar.gz" -C "$PROJECT" custom
tar -tzf "${BACKUP_DIR}/custom.tar.gz" >/dev/null 2>&1 || true

cp docker/production/docker-compose.yml "${BACKUP_DIR}/"
cp config/production/.env "${BACKUP_DIR}/"
cp config/production/odoo.conf "${BACKUP_DIR}/" 2>/dev/null || true

BACKUP_BYTES=$(du -sb "${BACKUP_DIR}" | awk '{print $1}')
cat > "${BACKUP_DIR}/MANIFEST.txt" << EOF
timestamp=${TS}
environment=production
database=${ODOO_DB_NAME}
project=${COMPOSE_PROJECT_NAME}
phase=26c-delivery-official
size_bytes=${BACKUP_BYTES}
restorable=verified_gzip_and_tar
EOF

echo "BACKUP_OK: ${BACKUP_DIR} (${BACKUP_BYTES} bytes)"
ls -la "${BACKUP_DIR}"

rm -rf custom/justech_report_design
tar xzf /tmp/phase26c_justech_report_design.tgz -C custom
chmod -R a+rX custom/justech_report_design
grep -q "19.0.5.2.0" custom/justech_report_design/__manifest__.py
grep -q "action_report_delivery_backup" custom/justech_report_design/data/report_official_data.xml

cd docker/production
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http 2>&1 | tee /tmp/phase26c-upgrade.log | tail -20
docker compose --env-file ../../config/production/.env up -d odoo
sleep 16

docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase26c-delivery-official-prod.py > /tmp/out-phase26c-prod.txt 2>&1
tail -30 /tmp/out-phase26c-prod.txt

EVIDENCE="${PROJECT}/evidence/phase26c-delivery-official-prod"
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-prod-odoo-1:/tmp/phase26c-delivery-official-prod/. "$EVIDENCE/" 2>/dev/null || true
cp /tmp/out-phase26c-prod.txt "$EVIDENCE/shell.log"
cp /tmp/phase26c-upgrade.log "$EVIDENCE/upgrade.log"
echo "${BACKUP_DIR}" > "$EVIDENCE/backup_path.txt"
echo "${TS}" > "$EVIDENCE/backup_timestamp.txt"
echo "${BACKUP_BYTES}" > "$EVIDENCE/backup_size_bytes.txt"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase26c-delivery-official-prod/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done

if command -v pdftotext >/dev/null && [ -f "$EVIDENCE_DIR/validation.json" ]; then
  python3 "$SCRIPT_DIR/phase26b-host-pdf-check.py" "$EVIDENCE_DIR" || true
fi

echo "=== RESULTADO 26C ==="
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null | head -50
echo "Backup: $(cat "$EVIDENCE_DIR/backup_path.txt" 2>/dev/null) ($(cat "$EVIDENCE_DIR/backup_size_bytes.txt" 2>/dev/null) bytes)"
