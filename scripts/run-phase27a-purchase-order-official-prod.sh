#!/usr/bin/env bash
# Fase 27A — Backup PROD + Orden de Compra oficial Justech + validación
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase27a-purchase-order-official-prod"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/phase27a_justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase27a_justech_report_design.tgz \
  "${SCRIPT_DIR}/phase27a-purchase-order-official-prod.py" root@2.25.69.179:/tmp/

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
tar -tzf "${BACKUP_DIR}/filestore.tar.gz" >/dev/null

tar czf "${BACKUP_DIR}/custom.tar.gz" -C "$PROJECT" custom
tar -tzf "${BACKUP_DIR}/custom.tar.gz" >/dev/null

cp docker/production/docker-compose.yml "${BACKUP_DIR}/"
cp config/production/.env "${BACKUP_DIR}/"
cp config/production/odoo.conf "${BACKUP_DIR}/" 2>/dev/null || true

cat > "${BACKUP_DIR}/MANIFEST.txt" << EOF
timestamp=${TS}
environment=production
database=${ODOO_DB_NAME}
project=${COMPOSE_PROJECT_NAME}
phase=27a-purchase-order-official
restorable=verified_gzip_and_tar
EOF

echo "BACKUP_OK: ${BACKUP_DIR}"
ls -la "${BACKUP_DIR}"

rm -rf custom/justech_report_design
tar xzf /tmp/phase27a_justech_report_design.tgz -C custom
chmod -R a+rX custom/justech_report_design
grep -q "purchase.action_report_purchase_order" custom/justech_report_design/data/report_official_data.xml
test ! -f custom/justech_report_design/views/purchase_order_views.xml

cd docker/production
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http > /tmp/phase27a-upgrade.log 2>&1
tail -15 /tmp/phase27a-upgrade.log
docker compose --env-file ../../config/production/.env up -d odoo
sleep 14

docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase27a-purchase-order-official-prod.py > /tmp/out-phase27a-prod.txt 2>&1
tail -20 /tmp/out-phase27a-prod.txt

EVIDENCE="${PROJECT}/evidence/phase27a-purchase-order-official-prod"
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-prod-odoo-1:/tmp/phase27a-purchase-order-official-prod/. "$EVIDENCE/" 2>/dev/null || true
cp /tmp/out-phase27a-prod.txt "$EVIDENCE/shell.log"
echo "${BACKUP_DIR}" > "$EVIDENCE/backup_path.txt"
echo "${TS}" > "$EVIDENCE/backup_timestamp.txt"
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase27a-purchase-order-official-prod/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done

mkdir -p "$PROJECT_ROOT/packages/phase27a-purchase-order-official"
(cd "$PROJECT_ROOT/custom" && zip -r "$PROJECT_ROOT/packages/phase27a-purchase-order-official/justech_report_design-v19.0.7.1.0.zip" justech_report_design -x "*.pyc" -x "*__pycache__*")
(cd "$EVIDENCE_DIR" && zip -r "$PROJECT_ROOT/packages/phase27a-purchase-order-official/phase27a-evidence.zip" . 2>/dev/null || true)

echo "=== RESULTADO ==="
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null || cat "$EVIDENCE_DIR/shell.log" | tail -30
echo "Backup: $(cat "$EVIDENCE_DIR/backup_path.txt" 2>/dev/null)"
