#!/usr/bin/env bash
# Valida backup justech_dev: restore real BD + filestore temporal + assets físicos.
set -euo pipefail

BACKUP_DIR="${1:?Usage: $0 /path/to/backup/dir}"
DB_SOURCE="justech_dev"
DB_TEST="justech_dev_restore_validate"
FS_TEST="/tmp/filestore_restore_validate_${DB_TEST}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="/opt/odoo-dev/conf/odoo-dev.conf"
MIN_FILESTORE_BYTES=$((100 * 1024 * 1024))

DUMP="${BACKUP_DIR}/${DB_SOURCE}.dump"
FS_ARCHIVE="${BACKUP_DIR}/filestore_${DB_SOURCE}.tar.gz"

fail() { echo "RESTORE_VALIDATE_FAIL: $*" >&2; exit 1; }

[[ -s "${DUMP}" ]] || fail "dump missing or empty: ${DUMP}"
[[ -s "${FS_ARCHIVE}" ]] || fail "filestore archive missing or empty: ${FS_ARCHIVE}"

FS_SIZE=$(stat -c%s "${FS_ARCHIVE}" 2>/dev/null || stat -f%z "${FS_ARCHIVE}")
if [[ "${FS_SIZE}" -lt "${MIN_FILESTORE_BYTES}" ]]; then
  fail "filestore archive too small (${FS_SIZE} bytes, min ${MIN_FILESTORE_BYTES})"
fi

echo "==> Crear BD temporal ${DB_TEST}"
sudo -u odoo dropdb --if-exists "${DB_TEST}"
sudo -u odoo createdb -O odoo "${DB_TEST}"

echo "==> Restaurar dump"
if ! sudo -u odoo pg_restore -d "${DB_TEST}" "${DUMP}" 2>"${BACKUP_DIR}/.pg_restore_err.tmp"; then
  tail -20 "${BACKUP_DIR}/.pg_restore_err.tmp" || true
  fail "pg_restore failed"
fi

echo "==> Extraer filestore temporal"
rm -rf "${FS_TEST}"
mkdir -p "${FS_TEST}"
tar -xzf "${FS_ARCHIVE}" -C "${FS_TEST}"
RESTORED_FS="${FS_TEST}/${DB_SOURCE}"
[[ -d "${RESTORED_FS}" ]] || fail "extracted filestore path missing: ${RESTORED_FS}"

FS_DIR_SIZE=$(du -sb "${RESTORED_FS}" | awk '{print $1}')
if [[ "${FS_DIR_SIZE}" -lt "${MIN_FILESTORE_BYTES}" ]]; then
  fail "restored filestore dir too small (${FS_DIR_SIZE} bytes)"
fi

echo "==> Verificar conteos históricos"
sudo -u odoo psql -d "${DB_TEST}" -t -c "
SELECT 'posted' AS k, COUNT(*)::text FROM account_move WHERE state='posted'
UNION ALL SELECT 'ncf_adel', COUNT(*)::text FROM account_move WHERE state='posted' AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
UNION ALL SELECT 'reconciles', COUNT(*)::text FROM account_partial_reconcile
UNION ALL SELECT 'payments', COUNT(*)::text FROM account_payment WHERE state IN ('paid','in_process');
"

echo "==> Validar assets físicos en restore"
sudo -u odoo /usr/bin/odoo shell -c "${CONF}" -d "${DB_TEST}" --no-http <<PY
import json, sys
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-validate-assets.py").read())
result = validate(env, filestore_root="${RESTORED_FS}", label="restore_validate")
print(json.dumps(result, indent=2, default=str))
sys.exit(0 if result["ok"] else 1)
PY

echo "==> Eliminar BD temporal"
sudo -u odoo dropdb "${DB_TEST}"
rm -rf "${FS_TEST}"

echo "RESTORE_VALIDATE_OK"
