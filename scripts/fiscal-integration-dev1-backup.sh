#!/usr/bin/env bash
# Backup completo erp.justech.do (justech_dev) — obligatorio antes de integración fiscal.
set -euo pipefail

TS="${1:-$(date +%Y%m%d_%H%M%S)}"
BACKUP_ROOT="/opt/odoo-dev/backups/fiscal-integration-dev1-${TS}"
DB="justech_dev"
CONF="/opt/odoo-dev/conf/odoo-dev.conf"
FILESTORE="/opt/odoo-dev/data/filestore/${DB}"
ADDONS_JUSTGROUP="/opt/odoo-dev/custom-addons/justgroup/custom_addons"
ADDONS_LEGACY="/usr/lib/odoo/custom-addons"
EVIDENCE_SRC="/opt/odoo-dev/evidence"

mkdir -p "${BACKUP_ROOT}"
echo "Backup destino: ${BACKUP_ROOT}"

echo "==> PostgreSQL dump (${DB})"
sudo -u odoo pg_dump -Fc "${DB}" > "${BACKUP_ROOT}/${DB}.dump"
test -s "${BACKUP_ROOT}/${DB}.dump"

echo "==> Filestore"
tar -czf "${BACKUP_ROOT}/filestore_${DB}.tar.gz" -C "$(dirname "${FILESTORE}")" "$(basename "${FILESTORE}")"
test -s "${BACKUP_ROOT}/filestore_${DB}.tar.gz"

echo "==> Custom addons (justgroup + legacy)"
tar -czf "${BACKUP_ROOT}/custom_addons_justgroup.tar.gz" -C "$(dirname "${ADDONS_JUSTGROUP}")" "$(basename "${ADDONS_JUSTGROUP}")"
tar -czf "${BACKUP_ROOT}/custom_addons_legacy.tar.gz" -C "$(dirname "${ADDONS_LEGACY}")" "$(basename "${ADDONS_LEGACY}")"
test -s "${BACKUP_ROOT}/custom_addons_justgroup.tar.gz"

echo "==> Configuración Odoo"
cp "${CONF}" "${BACKUP_ROOT}/odoo-dev.conf"

echo "==> Evidencias (si existen)"
if [ -d "${EVIDENCE_SRC}" ]; then
  tar -czf "${BACKUP_ROOT}/evidence_snapshot.tar.gz" -C "$(dirname "${EVIDENCE_SRC}")" "$(basename "${EVIDENCE_SRC}")"
fi

echo "==> Baseline integridad pre-cambio"
sudo -u odoo /usr/bin/odoo shell -c "${CONF}" -d "${DB}" --no-http <<'PY' > "${BACKUP_ROOT}/baseline_pre_change.json"
exec(open("/opt/odoo-dev/scripts/fiscal-integration-a001-baseline.py").read())
PY

cat > "${BACKUP_ROOT}/MANIFEST.md" <<EOF
# Backup erp.justech.do — ${TS}

| Componente | Archivo |
|------------|---------|
| BD ${DB} | ${DB}.dump |
| Filestore | filestore_${DB}.tar.gz |
| Addons justgroup | custom_addons_justgroup.tar.gz |
| Addons legacy | custom_addons_legacy.tar.gz |
| Config | odoo-dev.conf |
| Baseline | baseline_pre_change.json |

## Restauración rápida

\`\`\`bash
sudo systemctl stop odoo-dev
sudo -u odoo dropdb ${DB} && sudo -u odoo createdb -O odoo ${DB}
sudo -u odoo pg_restore -d ${DB} ${BACKUP_ROOT}/${DB}.dump
rm -rf ${FILESTORE} && mkdir -p ${FILESTORE}
tar -xzf ${BACKUP_ROOT}/filestore_${DB}.tar.gz -C /opt/odoo-dev/data/filestore/
sudo systemctl start odoo-dev
\`\`\`
EOF

echo "${BACKUP_ROOT}" > "${BACKUP_ROOT}/BACKUP_PATH.txt"
echo "BACKUP_OK ${BACKUP_ROOT}"
