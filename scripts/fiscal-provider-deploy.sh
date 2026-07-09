#!/usr/bin/env bash
# Despliegue controlado Fiscal Data Provider — erp.justech.do / justech_dev
set -euo pipefail

CONF="/opt/odoo-dev/conf/odoo-dev.conf"
DB="justech_dev"
FILESTORE="/opt/odoo-dev/data/filestore/${DB}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_CUSTOM="${REPO_CUSTOM:-/opt/odoo-dev/src/jaios/custom}"
ADDONS="/opt/odoo-dev/custom-addons/justgroup/custom_addons"
BASE_URL="${BASE_URL:-https://erp.justech.do}"
PERIOD="${PERIOD:-202606}"
TARGET_NCF="${TARGET_NCF:-E310000019120}"
EV="/opt/odoo-dev/evidence/fiscal-integration/FDP-deploy-$(date +%Y%m%d_%H%M%S)"

mkdir -p "$EV"
exec > >(tee -a "$EV/run.log") 2>&1

fail() {
  echo "FDP_DEPLOY_FAIL: $*" >&2
  exit 1
}

rollback_now() {
  local backup="$1"
  echo "==> ROLLBACK desde $backup"
  systemctl stop odoo-dev
  sudo -u odoo dropdb --if-exists "$DB"
  sudo -u odoo createdb -O odoo "$DB"
  sudo -u odoo pg_restore -d "$DB" "$backup/${DB}.dump"
  rm -rf "$FILESTORE"
  mkdir -p "$(dirname "$FILESTORE")"
  tar -xzf "$backup/filestore_${DB}.tar.gz" -C "$(dirname "$FILESTORE")"
  chown -R odoo:odoo "$FILESTORE"
  systemctl start odoo-dev
  echo "ROLLBACK_DONE"
}

echo "========================================"
echo "FDP DEPLOY — $(date -Iseconds)"
echo "EVIDENCE=$EV"
echo "PERIOD=$PERIOD"
echo "========================================"

echo "==> PRE: healthcheck completo"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY
grep -q '"passed": true' "$EV/pre_healthcheck.json" || fail "pre healthcheck failed"

echo "==> PRE: baseline histórico"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_baseline.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-post-validate.py").read())
PY

echo "==> PRE: validate full"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_validate_full.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-validate-full.py").read())
PY
grep -q '"passed": true' "$EV/pre_validate_full.json" || fail "pre validate_full failed"

echo "==> PRE: validación 606 período ${PERIOD}"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/pre_606_${PERIOD}.json"
import sys
sys.argv = ["", "${PERIOD}"]
exec(open("${SCRIPT_DIR}/fiscal-integration-606-period-validate.py").read())
PY

echo "==> PRE: smoke provider (si ya existe)"
if sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY 2>/dev/null | tee "$EV/pre_provider_smoke.json"
provider = env.get("justech.do.fiscal.data.provider")
if not provider:
    print('{"ok": false, "reason": "provider_not_installed_yet"}')
else:
    import json
    Move = env["account.move"]
    move = Move.search([("l10n_latam_document_number", "=", "${TARGET_NCF}"), ("state", "=", "posted")], limit=1)
    out = {"ok": bool(move), "provider_installed": True, "move_id": move.id if move else None}
    if move:
        out["provider_ncf"] = provider.get_ncf(move)
        out["justech_do_ncf"] = getattr(move, "justech_do_ncf", None)
    print(json.dumps(out, indent=2, default=str))
PY
then
  true
fi

echo "==> BACKUP blindado pre-upgrade"
BACKUP_OUT=$(bash "${SCRIPT_DIR}/fiscal-integration-dev1-backup.sh" "$(date +%Y%m%d_%H%M%S)" "fdp-pre" 2>&1 | tee "$EV/backup.log" | tail -1)
BACKUP_PATH=$(echo "$BACKUP_OUT" | awk '{print $NF}')
[[ -d "$BACKUP_PATH" ]] || fail "backup failed: $BACKUP_OUT"
echo "$BACKUP_PATH" > "$EV/BACKUP_PATH.txt"

echo "==> Sync código (base + reports only)"
for mod in justech_l10n_do_base justech_l10n_do_reports; do
  src="${REPO_CUSTOM}/${mod}"
  dst="${ADDONS}/${mod}"
  [[ -d "$src" ]] || fail "missing source $src"
  rsync -a --delete "${src}/" "${dst}/"
  chown -R odoo:odoo "${dst}"
done
# scripts (skip if already in place)
for s in fiscal-provider-smoke.py fiscal-integration-606-period-validate.py; do
  src="${SCRIPT_DIR}/${s}"
  dst="/opt/odoo-dev/scripts/${s}"
  if [[ "$(readlink -f "$src" 2>/dev/null || echo "$src")" != "$(readlink -f "$dst" 2>/dev/null || echo "$dst")" ]]; then
    install -m 0755 "$src" "$dst"
  fi
done

echo "==> SQL: fiscal Justech OFF (4 empresas)"
sudo -u odoo psql -d "$DB" -c "UPDATE res_company SET justech_do_fiscal_enabled = false WHERE justech_do_fiscal_enabled IS NOT FALSE;"

echo "==> UPGRADE: justech_l10n_do_base, justech_l10n_do_reports"
if ! sudo -u odoo /usr/bin/odoo -c "$CONF" -d "$DB" \
  -u justech_l10n_do_base,justech_l10n_do_reports \
  --stop-after-init --no-http 2>&1 | tee "$EV/upgrade.log"; then
  rollback_now "$BACKUP_PATH"
  fail "upgrade failed — rollback executed"
fi
if grep -iE 'ParseError|Traceback|CRITICAL' "$EV/upgrade.log" | grep -v DeprecationWarning | grep -v '^$' | head -1 | grep -q .; then
  rollback_now "$BACKUP_PATH"
  fail "upgrade log errors — rollback executed"
fi

echo "==> POST: healthcheck"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_healthcheck.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-env-healthcheck.py").read())
PY
grep -q '"passed": true' "$EV/post_healthcheck.json" || fail "post healthcheck failed"

echo "==> POST: baseline"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_baseline.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-post-validate.py").read())
PY

echo "==> POST: validate full"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_validate_full.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-validate-full.py").read())
PY
grep -q '"passed": true' "$EV/post_validate_full.json" || fail "post validate_full failed"

echo "==> POST: assets físicos"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_assets.json"
exec(open("${SCRIPT_DIR}/fiscal-integration-dev1-validate-assets.py").read())
import json, sys
result = validate(env, filestore_root="${FILESTORE}", label="post_fdp")
print(json.dumps(result, indent=2, default=str))
sys.exit(0 if result["ok"] else 1)
PY

echo "==> POST: assets HTTP"
ASSET_URLS=$(sudo -u odoo psql -d "$DB" -t -A -c "
SELECT url FROM ir_attachment
WHERE url LIKE '/web/assets/%' AND name LIKE '%.min.%'
ORDER BY write_date DESC LIMIT 3;
")
while IFS= read -r url; do
  [[ -z "$url" ]] && continue
  code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${url}")
  echo "asset ${code} ${url}"
  [[ "$code" == "200" ]] || fail "asset HTTP $code $url"
done <<< "$ASSET_URLS"

LOGIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/web/login")
echo "login ${LOGIN_CODE}"
[[ "$LOGIN_CODE" == "200" ]] || fail "login not 200"

echo "==> POST: provider smoke ${TARGET_NCF}"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_provider_smoke.json"
import json
provider = env["justech.do.fiscal.data.provider"]
exporter = env["justech.do.dgii.606.exporter"]
Move = env["account.move"]
move = Move.search([("l10n_latam_document_number", "=", "${TARGET_NCF}"), ("state", "=", "posted")], limit=1)
from datetime import date
result = {
  "target_ncf": "${TARGET_NCF}",
  "move_found": bool(move),
  "move_id": move.id if move else None,
  "provider_ncf": provider.get_ncf(move) if move else None,
  "provider_source": provider.get_supported_sources(move) if move else None,
  "justech_do_ncf": getattr(move, "justech_do_ncf", None) if move else None,
  "l10n_latam_document_number": getattr(move, "l10n_latam_document_number", None) if move else None,
}
if move:
    dfrom = move.invoice_date.replace(day=1) if move.invoice_date else date.today().replace(day=1)
    dto = move.invoice_date or dfrom
    errs = exporter._dgii_validate_single_move(move, dfrom, dto)
    result["606_ncf_errors"] = [e for e in errs if "NCF" in e]
    result["606_valid_for_ncf"] = not result["606_ncf_errors"]
result["ok"] = bool(move and result.get("provider_ncf") == "${TARGET_NCF}" and result.get("606_valid_for_ncf"))
print(json.dumps(result, indent=2, default=str))
PY
grep -q '"ok": true' "$EV/post_provider_smoke.json" || fail "provider smoke failed"

echo "==> POST: validación 606 período ${PERIOD}"
sudo -u odoo /usr/bin/odoo shell -c "$CONF" -d "$DB" --no-http <<PY | tee "$EV/post_606_${PERIOD}.json"
import sys
sys.argv = ["", "${PERIOD}"]
exec(open("${SCRIPT_DIR}/fiscal-integration-606-period-validate.py").read())
PY

echo "==> Comparativa 606 ${PERIOD}"
python3 <<'PY' | tee "$EV/606_compare_${PERIOD}.json"
import json
from pathlib import Path
ev = Path("${EV}")
pre = json.loads((ev / "pre_606_${PERIOD}.json").read_text())
post = json.loads((ev / "post_606_${PERIOD}.json").read_text())
cmp = {
    "period": "${PERIOD}",
    "pre_total_errors": pre.get("total_errors"),
    "post_total_errors": post.get("total_errors"),
    "delta_total_errors": (post.get("total_errors") or 0) - (pre.get("total_errors") or 0),
    "pre_missing_ncf": pre.get("missing_ncf_count"),
    "post_missing_ncf": post.get("missing_ncf_count"),
    "resolved_missing_ncf": (pre.get("missing_ncf_count") or 0) - (post.get("missing_ncf_count") or 0),
    "pre_errors_by_category": pre.get("errors_by_category"),
    "post_errors_by_category": post.get("errors_by_category"),
    "pre_target": pre.get("target_ecf_E310000019120"),
    "post_target": post.get("target_ecf_E310000019120"),
    "remaining_errors_sample": post.get("errors_sample"),
}
print(json.dumps(cmp, indent=2, default=str))
PY

echo "FDP_DEPLOY_OK evidence=$EV backup=$BACKUP_PATH"
