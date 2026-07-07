#!/usr/bin/env bash
# UX-FLOW-FIX — Deploy PROD (commit 1eeb17b)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/ux-flow-fix-prod"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="${VPS:-root@2.25.69.179}"
REMOTE="/opt/odoo-projects/hellenia"
DEPLOY_COMMIT="${DEPLOY_COMMIT:-1eeb17ba756c9c776d34873fe8ee355af2b492b4}"
TS="$(date +%Y-%m-%d_%H%M%S)"
LOG="$EVIDENCE/deploy-${TS}.log"

mkdir -p "$EVIDENCE"
exec > >(tee -a "$LOG") 2>&1

echo "=== UX-FLOW-FIX PROD ==="
echo "Commit: $DEPLOY_COMMIT"
echo "Timestamp: $TS"

LOCAL_COMMIT="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
if [[ "$LOCAL_COMMIT" != "$DEPLOY_COMMIT" ]]; then
  echo "ERROR: HEAD local ($LOCAL_COMMIT) != commit aprobado ($DEPLOY_COMMIT)"
  exit 1
fi

SSH=(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$VPS")
SCP=(scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)

echo ""
echo "=== 1. Backup PROD completo ==="
BACKUP_PATH="$("${SSH[@]}" bash -s <<REMOTE
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
TS=$(date +%Y-%m-%d_%H%M%S)
DEST="\$PROJECT/backups/hellenia-prod/ux-flow-fix-\${TS}"
mkdir -p "\$DEST"
source "\$PROJECT/config/production/.env"

docker exec hellenia-prod-db-1 pg_dumpall -U "\${DB_USER}" | gzip > "\${DEST}/postgres_all.sql.gz"
VOL=\$(docker volume ls --format '{{.Name}}' | grep hellenia-prod_odoo-data | head -1)
docker run --rm -v "\${VOL}:/data:ro" -v "\${DEST}":/backup alpine \
  tar czf /backup/filestore.tar.gz -C /data .
tar czf "\${DEST}/custom_modules.tar.gz" -C "\$PROJECT/custom" \
  hellenia_ui hellenia_ux justech_admin justech_global_audit_log justech_l10n_do_reports
cp "\$PROJECT/config/production/.env" "\${DEST}/.env"
cp "\$PROJECT/docker/production/docker-compose.yml" "\${DEST}/"

test -s "\${DEST}/postgres_all.sql.gz"
test -s "\${DEST}/filestore.tar.gz"
test -s "\${DEST}/custom_modules.tar.gz"
gunzip -t "\${DEST}/postgres_all.sql.gz"

cat > "\${DEST}/MANIFEST.txt" << EOF
timestamp=\${TS}
type=ux-flow-fix-pre-deploy
environment=production
database=hellenia_prod
commit=${DEPLOY_COMMIT}
postgres=postgres_all.sql.gz
filestore=filestore.tar.gz
custom=custom_modules.tar.gz
EOF

echo "\${DEST}"
REMOTE
)"
echo "Backup: $BACKUP_PATH"
echo "$BACKUP_PATH" > "$EVIDENCE/BACKUP_PATH.txt"
"${SCP[@]}" "$VPS:${BACKUP_PATH}/MANIFEST.txt" "$EVIDENCE/BACKUP_MANIFEST.txt"

echo ""
echo "=== 2. Verificar backup ==="
"${SSH[@]}" bash -s <<REMOTE
set -euo pipefail
DEST="$BACKUP_PATH"
test -s "\$DEST/postgres_all.sql.gz"
test -s "\$DEST/filestore.tar.gz"
test -s "\$DEST/custom_modules.tar.gz"
gunzip -t "\$DEST/postgres_all.sql.gz"
echo "BACKUP_VERIFY=PASS"
REMOTE
echo "BACKUP_VERIFY=PASS" | tee "$EVIDENCE/BACKUP_VERIFY.txt"

echo ""
echo "=== 3. Sync módulos UX-FLOW-FIX ==="
for mod in hellenia_ui hellenia_ux; do
  rsync -az --delete -e "ssh -i $SSH_KEY" \
    "$PROJECT_ROOT/custom/${mod}/" \
    "$VPS:$REMOTE/custom/${mod}/"
done
for mod in justech_admin justech_global_audit_log justech_l10n_do_reports; do
  rsync -az -e "ssh -i $SSH_KEY" \
    "$PROJECT_ROOT/custom/${mod}/" \
    "$VPS:$REMOTE/custom/${mod}/"
done

"${SCP[@]}" \
  "$SCRIPT_DIR/ux-flow-fix-validate.py" \
  "$SCRIPT_DIR/ux-flow-fix-prod-smoke.py" \
  "$VPS:/tmp/"

echo ""
echo "=== 4. Upgrade controlado ==="
"${SSH[@]}" bash -s <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
UPLOG="/tmp/ux-flow-fix-upgrade.log"
docker compose --env-file ../../config/production/.env run --rm odoo odoo \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u hellenia_ui,hellenia_ux,justech_admin,justech_global_audit_log,justech_l10n_do_reports \
  --stop-after-init 2>&1 | tee "$UPLOG"
if grep -qE "CRITICAL|Traceback" "$UPLOG"; then
  echo "UPGRADE_RESULT=FAIL"
  exit 1
fi
echo "UPGRADE_RESULT=PASS"
REMOTE
echo "UPGRADE_RESULT=PASS" | tee "$EVIDENCE/UPGRADE_RESULT.txt"
"${SCP[@]}" "$VPS:/tmp/ux-flow-fix-upgrade.log" "$EVIDENCE/upgrade.log" 2>/dev/null || true

echo ""
echo "=== 5. Menús + limpiar assets/caché ==="
"${SSH[@]}" bash -s <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http <<'PY'
env["hellenia.ui.menu.customizer"].apply_ux_flow_fix_labels()
env.registry.clear_cache()
assets = env["ir.attachment"].sudo().search([("url", "like", "/web/assets/%")])
n = len(assets)
assets.unlink()
env.cr.commit()
print("menu_labels=applied deleted_assets", n)
PY
REMOTE

echo ""
echo "=== 6. Reiniciar Odoo ==="
"${SSH[@]}" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env restart odoo
sleep 15
docker compose --env-file ../../config/production/.env ps odoo
REMOTE

echo ""
echo "=== 7. Validación PROD ==="
"${SSH[@]}" bash -s <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
EV=/tmp/ux-flow-fix-prod
mkdir -p "$EV"

docker compose --env-file ../../config/production/.env exec -T \
  -e UX_FLOW_FIX_EVIDENCE="$EV" odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/ux-flow-fix-validate.py 2>&1 | tee "$EV/validation_run.log"

docker compose --env-file ../../config/production/.env exec -T \
  -e UX_FLOW_FIX_EVIDENCE="$EV" odoo odoo shell \
  -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  --no-http < /tmp/ux-flow-fix-prod-smoke.py 2>&1 | tee "$EV/smoke_run.log"

/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod 2>&1 | tee "$EV/healthcheck.log"
REMOTE

"${SCP[@]}" "$VPS:/tmp/ux-flow-fix-prod/UX_FLOW_FIX_VALIDATION.json" "$EVIDENCE/" 2>/dev/null || true
"${SCP[@]}" "$VPS:/tmp/ux-flow-fix-prod/UX_FLOW_FIX_PROD_SMOKE.json" "$EVIDENCE/" 2>/dev/null || true
"${SCP[@]}" "$VPS:/tmp/ux-flow-fix-prod/validation_run.log" "$EVIDENCE/" 2>/dev/null || true
"${SCP[@]}" "$VPS:/tmp/ux-flow-fix-prod/smoke_run.log" "$EVIDENCE/" 2>/dev/null || true
"${SCP[@]}" "$VPS:/tmp/ux-flow-fix-prod/healthcheck.log" "$EVIDENCE/" 2>/dev/null || true
HC_JSON="$("${SSH[@]}" bash -c 'ls -1t /opt/odoo-projects/hellenia/evidence/healthcheck-prod-*.json 2>/dev/null | head -1')"
if [[ -n "$HC_JSON" ]]; then
  "${SCP[@]}" "$VPS:$HC_JSON" "$EVIDENCE/HEALTHCHECK.json" 2>/dev/null || true
fi

python3 - "$EVIDENCE" "$TS" "$BACKUP_PATH" "$DEPLOY_COMMIT" <<'PY'
import json
import sys
from pathlib import Path

ev = Path(sys.argv[1])
ts, backup, commit = sys.argv[2], sys.argv[3], sys.argv[4]

def load(name):
    p = ev / name
    return json.loads(p.read_text()) if p.exists() else {}

ux = load("UX_FLOW_FIX_VALIDATION.json")
smoke = load("UX_FLOW_FIX_PROD_SMOKE.json")
hc_pass = "RESULTADO: PASS" in (ev / "healthcheck.log").read_text(encoding="utf-8", errors="ignore") if (ev / "healthcheck.log").exists() else False

overall = ux.get("ok") and smoke.get("ok") and hc_pass
health = {
    "status": "PASS" if overall else "FAIL",
    "phase": "UX-FLOW-FIX-PROD",
    "commit": commit,
    "timestamp_utc": ux.get("timestamp_utc"),
    "url": "https://odoo.hellenia.cloud",
    "ux_flow_fix": ux.get("summary"),
    "smoke": smoke.get("summary"),
    "healthcheck": "PASS" if hc_pass else "FAIL",
}
(ev / "UX_FLOW_FIX_PROD_HEALTHCHECK.json").write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")

lines = [
    "# UX-FLOW-FIX — Despliegue PROD",
    "",
    f"**Fecha:** {ts}",
    f"**Commit:** `{commit}`",
    f"**Backup:** `{backup}`",
    f"**Veredicto:** {'PASS' if overall else 'FAIL'}",
    "",
    "## Validación UX (10 hallazgos)",
    "",
    f"- Resultado: **{ux.get('summary', 'N/A')}**",
    f"- Pendientes: {len(ux.get('pending', []))}",
    "",
    "## Smoke fiscal / multimoneda / Justech",
    "",
    f"- Resultado: **{smoke.get('summary', 'N/A')}**",
    "",
    "## Healthcheck",
    "",
    f"- **{'PASS' if hc_pass else 'FAIL'}**",
]
(ev / "UX_FLOW_FIX_PROD_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
(ev / "UX_FLOW_FIX_PROD_SUMMARY.md").write_text(
    "\n".join([
        "# UX-FLOW-FIX PROD — Resumen",
        "",
        f"- Commit: `{commit}`",
        f"- Backup: `{backup}`",
        f"- Upgrade: PASS",
        f"- UX 10/10: **{ux.get('summary', 'N/A')}**",
        f"- Smoke: **{smoke.get('summary', 'N/A')}**",
        f"- Healthcheck: **{'PASS' if hc_pass else 'FAIL'}**",
        f"- Blockers: {smoke.get('errors', []) + ux.get('pending', [])}",
    ]) + "\n",
    encoding="utf-8",
)
print("OVERALL=" + ("PASS" if overall else "FAIL"))
PY

echo ""
echo "=== UX-FLOW-FIX PROD COMPLETE ==="
echo "Evidence: $EVIDENCE"
echo "Log: $LOG"
