#!/usr/bin/env bash
# Cierre final Estándar Fiscal — erp.justech.do / justech_dev (sin merge).
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVIDENCE="/opt/odoo-dev/evidence/fiscal-closure"
TS="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/closure_${TS}.log") 2>&1

fail() { echo "CLOSURE_FAIL: $*"; exit 1; }

echo "========================================"
echo "CIERRE FINAL FISCAL — ${TS}"
echo "========================================"

echo "==> 1. Backup final blindado"
BACKUP_OUT=$(bash "${SCRIPT_DIR}/fiscal-integration-dev1-backup.sh" "${TS}" "fiscal-closure-final" 2>&1 | tee "$EVIDENCE/backup_${TS}.log" | tail -1)
BACKUP_PATH=$(echo "$BACKUP_OUT" | awk '{print $NF}')
[[ -d "$BACKUP_PATH" ]] || fail "backup failed"
echo "$BACKUP_PATH" > "$EVIDENCE/BACKUP_PATH.txt"

echo "==> Pre-cleanup snapshot"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EVIDENCE/pre_cleanup_${TS}.json"
import json
cr = env.cr
cr.execute("SELECT COUNT(*) FROM account_move WHERE state='posted'")
posted = cr.fetchone()[0]
cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
reconciles = cr.fetchone()[0]
print(json.dumps({"posted": posted, "reconciles": reconciles}))
PY

echo "==> 2. Limpieza datos de prueba (evidencias FISCALSTD)"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EVIDENCE/cleanup_${TS}.json"
exec(open("${SCRIPT_DIR}/fiscal-standard-cleanup.py").read())
PY
grep -q '"ok": true' "$EVIDENCE/cleanup_${TS}.json" || fail "cleanup errors"

echo "==> Post-cleanup snapshot"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EVIDENCE/post_cleanup_${TS}.json"
import json
cr = env.cr
cr.execute("SELECT COUNT(*) FROM account_move WHERE state='posted'")
posted = cr.fetchone()[0]
cr.execute("SELECT COUNT(*) FROM account_partial_reconcile")
reconciles = cr.fetchone()[0]
print(json.dumps({"posted": posted, "reconciles": reconciles}))
PY

echo "==> 3. Instalación limpia en justech_lab"
bash "${SCRIPT_DIR}/fiscal-clean-install-lab.sh"

echo "==> 4. Validación fiscal-standard-run.sh all"
export SCRIPT_DIR EVIDENCE="/opt/odoo-dev/evidence/fiscal-standard"
bash "${SCRIPT_DIR}/fiscal-standard-run.sh" all 2>&1 | tee "$EVIDENCE/fiscal_standard_all_${TS}.log"

echo "CLOSURE_OK ${EVIDENCE}"
