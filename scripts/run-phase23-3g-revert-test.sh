#!/usr/bin/env bash
# Fase 23.3G — Revert logo base — TEST
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase23-3g-revert-logo-base"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/hellenia_reports.tgz -C custom hellenia_reports
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/hellenia_reports.tgz \
  "${SCRIPT_DIR}/phase23-3g-revert-logo-test.py" root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -e
cd /opt/odoo-projects/hellenia
rm -rf custom/hellenia_reports && tar xzf /tmp/hellenia_reports.tgz -C custom
source config/test/.env
cd docker/test
docker compose --env-file ../../config/test/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u hellenia_reports --stop-after-init --no-http 2>&1 | tail -3
docker compose --env-file ../../config/test/.env up -d --force-recreate odoo
sleep 25
EVIDENCE=/opt/odoo-projects/hellenia/evidence/phase23-3g-revert-logo-base
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
TMP=/tmp/odoo-23.3g.txt
docker compose --env-file ../../config/test/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase23-3g-revert-logo-test.py > "$TMP" 2>&1
python3 <<'PY'
import json
d=open("/tmp/odoo-23.3g.txt").read()
m="PHASE23_3G:"
i=d.find(m)
r=json.loads(d[i+len(m):].strip())
open("/opt/odoo-projects/hellenia/evidence/phase23-3g-revert-logo-base/validation.json","w").write(json.dumps(r,indent=2,ensure_ascii=False))
print("PASS", r.get("pass"))
PY
docker cp hellenia-test-odoo-1:/tmp/phase23-3g-revert-logo-base/. "$EVIDENCE/" 2>/dev/null || true
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase23-3g-revert-logo-base/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true
