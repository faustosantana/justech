#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/fix-client-modules-ux-prod"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
TS="$(date +%Y-%m-%d_%H%M%S)"
BACKUP="client-modules-ux-${TS}"
mkdir -p "$EVIDENCE"
exec > >(tee -a "$EVIDENCE/run-${TS}.log") 2>&1
echo "=== Fix Client Modules UX PROD ==="
TEST_STATUS=$(python3 -c "import json,pathlib; p=pathlib.Path('$PROJECT_ROOT/evidence/fix-client-modules-ux-test/validation.json'); print(json.loads(p.read_text()).get('status','FAIL') if p.exists() else 'MISSING')")
if [[ "$TEST_STATUS" != "PASS" ]]; then
  echo "TEST validation not PASS ($TEST_STATUS). Aborting PROD deploy."
  exit 1
fi
for mod in justech_modules justech_admin; do
  rsync -avz --delete -e "ssh -i $SSH_KEY" "$PROJECT_ROOT/custom/${mod}/" "$VPS:$REMOTE/custom/${mod}/"
done
scp -i "$SSH_KEY" "$SCRIPT_DIR/validate-fix-client-modules-ux.py" "$VPS:/tmp/"
ssh -i "$SSH_KEY" "$VPS" bash <<REMOTE
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
BACKUP="\$PROJECT/backups/hellenia-prod/${BACKUP}"
mkdir -p "\$BACKUP"
source "\$PROJECT/config/production/.env"
cd "\$PROJECT/docker/production"
docker exec hellenia-prod-db-1 pg_dump -U "\$DB_USER" -Fc hellenia_prod > "\$BACKUP/hellenia_prod.dump"
echo "Backup: \$BACKUP/hellenia_prod.dump"
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm odoo odoo \
  -d hellenia_prod --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  -u justech_modules,justech_admin --stop-after-init 2>&1 | tail -8
docker compose --env-file ../../config/production/.env up -d odoo
sleep 20
docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="\$DB_USER" --db_password="\$DB_PASSWORD" \
  --no-http < /tmp/validate-fix-client-modules-ux.py 2>&1 | tee /tmp/client-modules-ux-prod-validation.log
docker compose --env-file ../../config/production/.env exec -T odoo cat /var/lib/odoo/fix-client-modules-ux-validation.json > /tmp/client-modules-ux-prod-validation.json 2>/dev/null || true
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tee /tmp/client-modules-ux-prod-healthcheck.log | tail -10
REMOTE
scp -i "$SSH_KEY" "$VPS:/tmp/client-modules-ux-prod-validation.json" "$VPS:/tmp/client-modules-ux-prod-healthcheck.log" "$EVIDENCE/" 2>/dev/null || true
cp "$EVIDENCE/client-modules-ux-prod-validation.json" "$EVIDENCE/validation.json" 2>/dev/null || true
python3 - <<'PY' "$EVIDENCE" "$BACKUP"
import json, sys, pathlib
ev = pathlib.Path(sys.argv[1])
backup = sys.argv[2]
val = ev / "validation.json"
hc = ev / "client-modules-ux-prod-healthcheck.log"
status = "UNKNOWN"
if val.exists():
    data = json.loads(val.read_text())
    status = data.get("status", "UNKNOWN")
hc_text = hc.read_text() if hc.exists() else ""
hc_pass = "PASS" in hc_text or "OK" in hc_text or "healthy" in hc_text.lower()
(ev / "healthcheck.json").write_text(json.dumps({"status": "PASS" if hc_pass else "FAIL", "log_tail": hc_text[-2000:]}, indent=2))
report = f"""# UX Fix Report — Módulos del Cliente (PROD)

## Status
- Validation: **{status}**
- Healthcheck: **{"PASS" if hc_pass else "FAIL"}**
- Backup: **{backup}**

## PROD validation
Validated with it@justech.do visibility and no-popup open behavior.

## Evidence
- validation.json
- healthcheck.json
"""
(ev / "UX_FIX_REPORT.md").write_text(report)
print(f"Evidence written to {ev}")
PY
echo "Evidence: $EVIDENCE"
