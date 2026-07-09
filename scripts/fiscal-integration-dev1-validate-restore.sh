#!/usr/bin/env bash
# Valida que un backup justech_dev puede restaurarse (BD de prueba temporal).
set -euo pipefail

BACKUP_DIR="${1:?Usage: $0 /path/to/backup/dir}"
DB_SOURCE="justech_dev"
DB_TEST="justech_dev_restore_validate"

DUMP="${BACKUP_DIR}/${DB_SOURCE}.dump"
test -s "${DUMP}"

echo "==> Crear BD temporal ${DB_TEST}"
sudo -u odoo dropdb --if-exists "${DB_TEST}"
sudo -u odoo createdb -O odoo "${DB_TEST}"

echo "==> Restaurar dump"
sudo -u odoo pg_restore -d "${DB_TEST}" "${DUMP}" 2>&1 | tail -5 || true

echo "==> Verificar conteos"
sudo -u odoo psql -d "${DB_TEST}" -t -c "
SELECT 'posted' AS k, COUNT(*)::text FROM account_move WHERE state='posted'
UNION ALL SELECT 'ncf_adel', COUNT(*)::text FROM account_move WHERE state='posted' AND l10n_latam_document_number IS NOT NULL AND l10n_latam_document_number != ''
UNION ALL SELECT 'reconciles', COUNT(*)::text FROM account_partial_reconcile
UNION ALL SELECT 'payments', COUNT(*)::text FROM account_payment WHERE state IN ('paid','in_process');
"

echo "==> Eliminar BD temporal"
sudo -u odoo dropdb "${DB_TEST}"

echo "RESTORE_VALIDATE_OK"
