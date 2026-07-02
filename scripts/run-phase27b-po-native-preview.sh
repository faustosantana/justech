#!/usr/bin/env bash
# Fase 27B — Vista previa nativa OC: TEST luego PROD (con backup)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET="${1:-test}"

if [[ "$TARGET" != "test" && "$TARGET" != "prod" ]]; then
  echo "Uso: $0 [test|prod]"
  exit 1
fi

if [[ "$TARGET" == "test" ]]; then
  ENV_FILE="config/test/.env"
  COMPOSE_DIR="docker/test"
  CONTAINER="hellenia-test-odoo-1"
  EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase27b-po-native-preview-test"
else
  ENV_FILE="config/production/.env"
  COMPOSE_DIR="docker/production"
  CONTAINER="hellenia-prod-odoo-1"
  EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase27b-po-native-preview-prod"
fi

mkdir -p "$EVIDENCE_DIR"
cd "$PROJECT_ROOT"
tar czf /tmp/phase27b_native_preview.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase27b_native_preview.tgz \
  "${SCRIPT_DIR}/phase27b-purchase-order-native-preview-validation.py" \
  root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<REMOTE
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
cd "\$PROJECT"
source ${ENV_FILE}
TS=\$(date +%Y-%m-%d_%H%M%S)

if [[ "${TARGET}" == "prod" ]]; then
  BACKUP_DIR="\${PROJECT}/backups/hellenia-prod/\${TS}"
  mkdir -p "\${BACKUP_DIR}"
  echo "=== BACKUP PRODUCCIÓN \${TS} ==="
  docker exec hellenia-prod-db-1 pg_dumpall -U "\${DB_USER}" | gzip > "\${BACKUP_DIR}/postgres_all.sql.gz"
  gzip -t "\${BACKUP_DIR}/postgres_all.sql.gz"
  docker run --rm -v hellenia-prod_odoo-data:/data:ro -v "\${BACKUP_DIR}":/backup alpine \
    tar czf /backup/filestore.tar.gz -C /data .
  tar -tzf "\${BACKUP_DIR}/filestore.tar.gz" >/dev/null
  tar czf "\${BACKUP_DIR}/custom.tar.gz" -C "\$PROJECT" custom
  tar -tzf "\${BACKUP_DIR}/custom.tar.gz" >/dev/null
  cp docker/production/docker-compose.yml "\${BACKUP_DIR}/"
  cp config/production/.env "\${BACKUP_DIR}/"
  echo "phase=27b-po-native-preview" >> "\${BACKUP_DIR}/MANIFEST.txt"
  echo "BACKUP_OK: \${BACKUP_DIR}"
fi

rm -rf custom/justech_report_design
tar xzf /tmp/phase27b_native_preview.tgz -C custom
chmod -R a+rX custom/justech_report_design
grep -q 'suffix="/preview"' custom/justech_report_design/models/purchase_order.py

cd ${COMPOSE_DIR}
docker compose --env-file ../../${ENV_FILE} stop odoo || true
docker compose --env-file ../../${ENV_FILE} run --rm -T odoo odoo \
  -d "\$ODOO_DB_NAME" --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http > /tmp/phase27b-upgrade.log 2>&1
tail -10 /tmp/phase27b-upgrade.log
docker compose --env-file ../../${ENV_FILE} up -d odoo
echo "Esperando Odoo healthy..."
for i in $(seq 1 30); do
  if docker compose --env-file ../../${ENV_FILE} ps odoo 2>/dev/null | grep -q "(healthy)"; then
    break
  fi
  sleep 2
done
sleep 5

docker compose --env-file ../../${ENV_FILE} exec -T odoo odoo shell \
  -d "\$ODOO_DB_NAME" --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" --no-http \
  < /tmp/phase27b-purchase-order-native-preview-validation.py > /tmp/out-phase27b-native.txt 2>&1
tail -10 /tmp/out-phase27b-native.txt

EVIDENCE="\${PROJECT}/evidence/phase27b-po-native-preview-${TARGET}"
mkdir -p "\$EVIDENCE" && chmod 777 "\$EVIDENCE"
docker cp ${CONTAINER}:/tmp/phase27b-po-native-preview-${TARGET}/. "\$EVIDENCE/" 2>/dev/null || true
if [[ "${TARGET}" == "prod" ]]; then
  echo "\${BACKUP_DIR}" > "\$EVIDENCE/backup_path.txt"
fi
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase27b-po-native-preview-${TARGET}/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done

echo "=== RESULTADO ${TARGET} ==="
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null || echo "validation missing"
echo "Backup: $(cat "$EVIDENCE_DIR/backup_path.txt" 2>/dev/null || echo n/a)"
