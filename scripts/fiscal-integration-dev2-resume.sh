#!/usr/bin/env bash
# DEV-2 resume — upgrade stack fiscal Justech en justech_dev (Adel activo, fiscal OFF).
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
ROLLBACK="/opt/odoo-dev/backups/fiscal-integration-stabilized-20260709_222306"
FILESTORE="/opt/odoo-dev/data/filestore/${DB}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EV="/opt/odoo-dev/evidence/fiscal-integration/DEV-2-resume-$(date +%Y%m%d_%H%M%S)"
ADDONS="/opt/odoo-dev/custom-addons/justgroup/custom_addons"
BASE_URL="${BASE_URL:-https://erp.justech.do}"

mkdir -p "$EV"
exec > >(tee -a "$EV/run.log") 2>&1

fail() {
  echo "DEV2_RESUME_FAIL: $*" >&2
  echo "ROLLBACK_BASELINE=$ROLLBACK" >&2
  exit 1
}

rollback_now() {
  echo "==> ROLLBACK al baseline estabilizado"
  systemctl stop odoo-dev
  sudo -u odoo dropdb --if-exists "$DB"
  sudo -u odoo createdb -O odoo "$DB"
  sudo -u odoo pg_restore -d "$DB" "$ROLLBACK/justech_dev.dump"
  rm -rf "$FILESTORE"
  mkdir -p "$(dirname "$FILESTORE")"
  tar -xzf "$ROLLBACK/filestore_${DB}.tar.gz" -C "$(dirname "$FILESTORE")"
  chown -R odoo:odoo "$FILESTORE"
  systemctl start odoo-dev
  echo "ROLLBACK_DONE"
}

echo "========================================"
echo "DEV-2 RESUME — $(date -Iseconds)"
echo "ROLLBACK=$ROLLBACK"
echo "EVIDENCE=$EV"
echo "========================================"

[[ -d "$ROLLBACK" ]] || fail "rollback backup missing: $ROLLBACK"
[[ -s "$ROLLBACK/justech_dev.dump" ]] || fail "rollback dump missing"

echo "==> PRE: healthcheck completo"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY

echo "==> PRE: baseline histórico"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_baseline.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-post-validate.py").read())
PY

echo "==> PRE: validate full (19 checks)"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_validate_full.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-validate-full.py").read())
PY
grep -q '"passed": true' "$EV/pre_validate_full.json" || fail "pre validate_full failed"

echo "==> PRE: assets físicos"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_assets.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-validate-assets.py").read())
import json, sys
result = validate(env, filestore_root="${FILESTORE}", label="pre_dev2")
print(json.dumps(result, indent=2, default=str))
sys.exit(0 if result["ok"] else 1)
PY

echo "==> Upgrade stack fiscal (base + ncf + reports)"
if ! sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$DB" \
  -u justech_l10n_do_base,justech_l10n_do_ncf,justech_l10n_do_reports \
  --stop-after-init --no-http 2>&1 | tee "$EV/upgrade.log" | tail -30; then
  echo "UPGRADE_FAILED — iniciando rollback"
  rollback_now
  fail "upgrade failed — rollback executed"
fi
if grep -iE 'ParseError|Traceback|CRITICAL' "$EV/upgrade.log" | grep -v DeprecationWarning; then
  echo "UPGRADE_LOG_ERRORS — iniciando rollback"
  rollback_now
  fail "upgrade log contains errors — rollback executed"
fi

echo "==> Fiscal Justech OFF (4 empresas)"
sudo -u odoo psql -d "$DB" -c "UPDATE res_company SET justech_do_fiscal_enabled = false;"
ENABLED=$(sudo -u odoo psql -d "$DB" -t -A -c "SELECT COUNT(*) FROM res_company WHERE justech_do_fiscal_enabled = true;")
[[ "$ENABLED" == "0" ]] || fail "fiscal still enabled on companies"

echo "==> POST: baseline histórico"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_baseline.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-post-validate.py").read())
PY

echo "==> POST: validate full"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_validate_full.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-validate-full.py").read())
PY
grep -q '"passed": true' "$EV/post_validate_full.json" || fail "post validate_full failed"

echo "==> POST: 606/607 read-only"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/reports_smoke.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev2-reports-smoke.py").read())
PY
grep -q '"ok": true' "$EV/reports_smoke.json" || fail "reports smoke failed"

echo "==> POST: healthcheck"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY
grep -q '"passed": true' "$EV/post_healthcheck.json" || fail "post healthcheck failed"

echo "==> POST: assets HTTP"
sudo -u odoo psql -d "$DB" -t -A -c "
SELECT url FROM ir_attachment
WHERE url LIKE '/web/assets/%' AND name LIKE '%.min.%'
ORDER BY write_date DESC LIMIT 3;
" | while IFS= read -r url; do
  [[ -z "$url" ]] && continue
  code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${url}")
  echo "asset ${code} ${url}" | tee -a "$EV/assets_http.txt"
  [[ "$code" == "200" ]] || fail "asset not 200: ${url}"
done

echo "$ROLLBACK" > "$EV/ROLLBACK_PATH.txt"
echo "DEV2_RESUME_OK evidence=$EV"
