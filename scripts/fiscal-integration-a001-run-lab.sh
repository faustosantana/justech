#!/usr/bin/env bash
# Fase A A-001 — validación justech_ncf_lab en erp.justech.do
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-ncf-lab.conf"
DB="justech_ncf_lab"
LOG="/opt/odoo-dev/logs/odoo-ncf-lab.log"
EVIDENCE_DIR="${1:-/tmp/fiscal-a001-evidence}"
mkdir -p "$EVIDENCE_DIR"

echo "==> Sync skipped (run from workstation rsync if needed)"
echo "==> Upgrade justech_l10n_do_ncf (no-op if current)"
sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$DB" -u justech_l10n_do_ncf \
  --stop-after-init --no-http 2>&1 | tail -5

echo "==> Tests justech_l10n_do_ncf"
sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$DB" --test-enable --stop-after-init \
  --no-http --log-level=test --test-tags=/justech_l10n_do_ncf 2>&1 | tail -5

TEST_RESULT=$(grep 'odoo.tests.result' "$LOG" | tail -1 || true)
echo "$TEST_RESULT" | tee "$EVIDENCE_DIR/test_result.txt"

echo "==> Integrity extended"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<'PY' | tee "$EVIDENCE_DIR/integrity.json"
exec(open("/opt/odoo-dev/scripts/fiscal-phase3-sprint2-lab-integrity.py").read())
PY

echo "==> Done. Evidence: $EVIDENCE_DIR"
