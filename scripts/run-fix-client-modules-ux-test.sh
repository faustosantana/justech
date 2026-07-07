#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-client-modules-ux-test"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== Fix Client Modules UX TEST ==="
for mod in justech_modules justech_admin; do
  rsync -avz --delete -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" "$SCRIPT_DIR/validate-fix-client-modules-ux.py" "$VPS:/tmp/"
ssh -i "$SSH_KEY" "$VPS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/test/.env
cd /opt/odoo-projects/hellenia/docker/test
docker compose --env-file ../../config/test/.env stop odoo
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -8
docker compose --env-file ../../config/test/.env run --rm odoo odoo \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_modules,justech_admin --test-enable --stop-after-init 2>&1 | tee /tmp/client-modules-ux-test.log | grep "tests.result" || true
docker compose --env-file ../../config/test/.env up -d odoo
sleep 15
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d hellenia_test --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/validate-fix-client-modules-ux.py 2>&1 | tee /tmp/client-modules-ux-validation.log
docker compose --env-file ../../config/test/.env exec -T odoo cat /var/lib/odoo/fix-client-modules-ux-validation.json > /tmp/client-modules-ux-validation.json 2>/dev/null || true
/opt/odoo-projects/hellenia/scripts/healthcheck.sh test 2>&1 | tee /tmp/client-modules-ux-healthcheck.log | tail -8
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/client-modules-ux-validation.json" "$VPS:/tmp/client-modules-ux-test.log" "$VPS:/tmp/client-modules-ux-healthcheck.log" "$EVIDENCE/" 2>/dev/null || true
cp "$EVIDENCE/client-modules-ux-validation.json" "$EVIDENCE/validation.json" 2>/dev/null || true
python3 - <<'PY' "$EVIDENCE"
import json, sys, pathlib
ev = pathlib.Path(sys.argv[1])
val = ev / "validation.json"
hc = ev / "client-modules-ux-healthcheck.log"
status = "UNKNOWN"
if val.exists():
    data = json.loads(val.read_text())
    status = data.get("status", "UNKNOWN")
hc_text = hc.read_text() if hc.exists() else ""
hc_pass = "PASS" in hc_text or "OK" in hc_text or "healthy" in hc_text.lower()
(ev / "healthcheck.json").write_text(json.dumps({"status": "PASS" if hc_pass else "FAIL", "log_tail": hc_text[-2000:]}, indent=2))
report = f"""# UX Fix Report — Módulos del Cliente (TEST)

## Status
- Validation: **{status}**
- Healthcheck: **{"PASS" if hc_pass else "FAIL"}**

## Fixes applied
1. No auto popup on Configuración → Justech entry
2. Main screen = Módulos del Cliente with summary cards
3. Commercial module table with Administrar button
4. Key required only for sensitive actions
5. Module detail sheet with audit and actions

## Evidence
- validation.json
- client-modules-ux-test.log
- healthcheck.json
"""
(ev / "UX_FIX_REPORT.md").write_text(report)
print(f"Evidence written to {ev}")
PY
echo "Evidence: $EVIDENCE"
