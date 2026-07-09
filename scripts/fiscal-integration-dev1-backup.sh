#!/usr/bin/env bash
# Backup completo erp.justech.do (justech_dev) — BLINDADO.
# Falla si filestore < 100MB, assets faltantes, restore inválido o /web/assets != 200.
set -euo pipefail

TS="${1:-$(date +%Y%m%d_%H%M%S)}"
PREFIX="${2:-dev1}"
BACKUP_ROOT="/opt/odoo-dev/backups/fiscal-integration-${PREFIX}-${TS}"
DB="justech_dev"
CONF="/opt/odoo-dev/conf/odoo-dev.conf"
FILESTORE="/opt/odoo-dev/data/filestore/${DB}"
ADDONS_JUSTGROUP="/opt/odoo-dev/custom-addons/justgroup/custom_addons"
ADDONS_LEGACY="/usr/lib/odoo/custom-addons"
EVIDENCE_SRC="/opt/odoo-dev/evidence"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIN_FILESTORE_BYTES=$((100 * 1024 * 1024))
BASE_URL="${BACKUP_BASE_URL:-https://erp.justech.do}"

fail() { echo "BACKUP_ABORT: $*" >&2; exit 1; }

bytes_of() {
  local p="$1"
  stat -c%s "${p}" 2>/dev/null || stat -f%z "${p}"
}

dir_bytes() {
  du -sb "$1" | awk '{print $1}'
}

echo "========================================"
echo "BACKUP BLINDADO erp.justech.do — ${TS}"
echo "========================================"

echo "==> PRE-CHECK 1/4: filestore vivo >= 100MB"
[[ -d "${FILESTORE}" ]] || fail "filestore path missing: ${FILESTORE}"
LIVE_FS_BYTES=$(dir_bytes "${FILESTORE}")
echo "filestore_live_bytes=${LIVE_FS_BYTES}"
if [[ "${LIVE_FS_BYTES}" -lt "${MIN_FILESTORE_BYTES}" ]]; then
  fail "live filestore too small (${LIVE_FS_BYTES} bytes, min ${MIN_FILESTORE_BYTES})"
fi

echo "==> PRE-CHECK 2/4: assets físicos en ir_attachment"
sudo -u odoo /usr/bin/odoo shell -c "${CONF}" -d "${DB}" --no-http <<PY
import json, sys
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-validate-assets.py").read())
result = validate(env, filestore_root="${FILESTORE}", label="pre_backup")
print(json.dumps(result, indent=2, default=str))
sys.exit(0 if result["ok"] else 1)
PY

echo "==> PRE-CHECK 3/4: /web/assets responde 200 (live)"
ASSET_URLS=$(sudo -u odoo psql -d "${DB}" -t -A -c "
SELECT url FROM ir_attachment
WHERE url LIKE '/web/assets/%' AND name LIKE '%.min.%'
ORDER BY write_date DESC LIMIT 5;
" | grep -v '^$' || true)
[[ -n "${ASSET_URLS}" ]] || fail "no asset URLs found in ir_attachment"

while IFS= read -r url; do
  [[ -z "${url}" ]] && continue
  code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${url}")
  echo "asset_check ${code} ${url}"
  [[ "${code}" == "200" ]] || fail "asset URL not 200: ${url} (code=${code})"
done <<< "${ASSET_URLS}"

echo "==> PRE-CHECK 4/4: login responde 200"
LOGIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/web/login")
echo "login_check ${LOGIN_CODE}"
[[ "${LOGIN_CODE}" == "200" ]] || fail "login not 200 (code=${LOGIN_CODE})"

mkdir -p "${BACKUP_ROOT}"
echo "Backup destino: ${BACKUP_ROOT}"

echo "==> PostgreSQL dump (${DB})"
sudo -u odoo pg_dump -Fc "${DB}" > "${BACKUP_ROOT}/${DB}.dump"
test -s "${BACKUP_ROOT}/${DB}.dump"

echo "==> Filestore tar"
tar -czf "${BACKUP_ROOT}/filestore_${DB}.tar.gz" -C "$(dirname "${FILESTORE}")" "$(basename "${FILESTORE}")"
ARCHIVE_BYTES=$(bytes_of "${BACKUP_ROOT}/filestore_${DB}.tar.gz")
echo "filestore_archive_bytes=${ARCHIVE_BYTES}"
if [[ "${ARCHIVE_BYTES}" -lt "${MIN_FILESTORE_BYTES}" ]]; then
  fail "backup filestore archive too small (${ARCHIVE_BYTES} bytes)"
fi

echo "==> Custom addons (justgroup + legacy)"
tar -czf "${BACKUP_ROOT}/custom_addons_justgroup.tar.gz" -C "$(dirname "${ADDONS_JUSTGROUP}")" "$(basename "${ADDONS_JUSTGROUP}")"
tar -czf "${BACKUP_ROOT}/custom_addons_legacy.tar.gz" -C "$(dirname "${ADDONS_LEGACY}")" "$(basename "${ADDONS_LEGACY}")"
test -s "${BACKUP_ROOT}/custom_addons_justgroup.tar.gz"

echo "==> Configuración Odoo"
cp "${CONF}" "${BACKUP_ROOT}/odoo-dev.conf"

echo "==> Evidencias (si existen)"
if [[ -d "${EVIDENCE_SRC}" ]]; then
  tar -czf "${BACKUP_ROOT}/evidence_snapshot.tar.gz" -C "$(dirname "${EVIDENCE_SRC}")" "$(basename "${EVIDENCE_SRC}")"
fi

echo "==> Baseline integridad pre-cambio"
sudo -u odoo /usr/bin/odoo shell -c "${CONF}" -d "${DB}" --no-http <<'PY' > "${BACKUP_ROOT}/baseline_pre_change.json"
exec(open("/opt/odoo-dev/scripts/fiscal-integration-a001-baseline.py").read())
PY

echo "==> POST-CHECK: restore real BD + filestore temporal"
bash "${SCRIPT_DIR}/fiscal-integration-dev1-validate-restore.sh" "${BACKUP_ROOT}"

cat > "${BACKUP_ROOT}/MANIFEST.md" <<EOF
# Backup BLINDADO erp.justech.do — ${TS}

| Componente | Archivo |
|------------|---------|
| BD ${DB} | ${DB}.dump |
| Filestore | filestore_${DB}.tar.gz (>= 100MB validado) |
| Addons justgroup | custom_addons_justgroup.tar.gz |
| Addons legacy | custom_addons_legacy.tar.gz |
| Config | odoo-dev.conf |
| Baseline | baseline_pre_change.json |

## Validaciones ejecutadas

- Filestore vivo >= 100MB
- Assets físicos en ir_attachment
- /web/assets HTTP 200 (live)
- Restore BD + filestore en temporal
- Assets físicos post-restore

## Restauración rápida

\`\`\`bash
sudo systemctl stop odoo-dev
sudo -u odoo dropdb ${DB} && sudo -u odoo createdb -O odoo ${DB}
sudo -u odoo pg_restore -d ${DB} ${BACKUP_ROOT}/${DB}.dump
rm -rf ${FILESTORE} && mkdir -p ${FILESTORE}
tar -xzf ${BACKUP_ROOT}/filestore_${DB}.tar.gz -C /opt/odoo-dev/data/filestore/
chown -R odoo:odoo ${FILESTORE}
sudo systemctl start odoo-dev
\`\`\`
EOF

echo "${BACKUP_ROOT}" > "${BACKUP_ROOT}/BACKUP_PATH.txt"
echo "BACKUP_OK ${BACKUP_ROOT}"
