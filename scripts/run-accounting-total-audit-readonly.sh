#!/usr/bin/env bash
# Auditoría contable total — SOLO LECTURA (P1/P2)
# - No -u / -i módulos
# - No create/write/unlink (script Python read-only)
# - DEV + TEST + PROD (PROD confirmado read-only)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/accounting-total-audit-readonly"
SSH_KEY="${HOME}/.ssh/hellenia_vps_ed25519"
SSH_HOST="root@2.25.69.179"
AUDIT_SCRIPT="accounting-total-audit-readonly.py"
TS="$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$EVIDENCE_DIR"

echo "=== Accounting total audit (read-only) ==="
echo "Evidence: $EVIDENCE_DIR"
echo "Timestamp: $TS"

scp -i "$SSH_KEY" \
  "${SCRIPT_DIR}/${AUDIT_SCRIPT}" \
  "${SSH_HOST}:/tmp/${AUDIT_SCRIPT}"

ssh -i "$SSH_KEY" "$SSH_HOST" "AUDIT_SCRIPT=/tmp/${AUDIT_SCRIPT}" bash -s <<'REMOTE'
set -euo pipefail
EVIDENCE_BASE="/opt/odoo-projects/hellenia/evidence/accounting-total-audit-readonly"
mkdir -p "$EVIDENCE_BASE"

run_env() {
  local ENV_NAME="$1"
  local COMPOSE_DIR="$2"
  local ENV_FILE="$3"
  local OUT_TAG="$4"

  echo "--- Running read-only audit: $ENV_NAME ---"
  cd /opt/odoo-projects/hellenia
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  cd "$COMPOSE_DIR"

  if ! docker compose --env-file "$ENV_FILE" ps --status running odoo 2>/dev/null | grep -q odoo; then
    echo "SKIP $ENV_NAME: contenedor odoo no running"
    echo "{\"skipped\": true, \"reason\": \"odoo container not running\", \"environment\": \"$OUT_TAG\"}" > "$EVIDENCE_BASE/${OUT_TAG}-skipped.json"
    return 0
  fi

  set +e
  docker compose --env-file "$ENV_FILE" exec -T odoo odoo shell \
    -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
    < "$AUDIT_SCRIPT" > "/tmp/audit-${OUT_TAG}.txt" 2>&1
  local rc=$?
  set -e

  OUT_TAG="$OUT_TAG" EVIDENCE_BASE="$EVIDENCE_BASE" RC="$rc" python3 -c "
import json, os, pathlib
out_tag = os.environ['OUT_TAG']
evidence = os.environ['EVIDENCE_BASE']
rc = int(os.environ['RC'])
raw = pathlib.Path(f'/tmp/audit-{out_tag}.txt').read_text(errors='replace')
marker = 'ACCOUNTING_TOTAL_AUDIT:'
out = pathlib.Path(f'{evidence}/{out_tag}.json')
pathlib.Path(f'{evidence}/{out_tag}-raw.txt').write_text(raw)
if marker in raw:
    data = json.loads(raw[raw.find(marker)+len(marker):].strip())
    data['runner_exit_code'] = rc
    data['runner_mode'] = 'read_only_confirmed'
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print('OK', out_tag, 'pass=', data.get('pass'), 'critical=', data.get('summary', {}).get('critical_count'))
else:
    fail = {'environment': out_tag, 'runner_exit_code': rc, 'ok': False, 'error': 'marker not found', 'tail': raw[-4000:]}
    out.write_text(json.dumps(fail, indent=2, ensure_ascii=False))
    print('FAIL', out_tag, 'exit', rc)
    print(raw[-2000:])
"
}

run_env "DEV"  "/opt/odoo-projects/hellenia/docker/dev"         "/opt/odoo-projects/hellenia/config/dev/.env"         "dev"
run_env "TEST" "/opt/odoo-projects/hellenia/docker/test"        "/opt/odoo-projects/hellenia/config/test/.env"        "test"
run_env "PROD" "/opt/odoo-projects/hellenia/docker/production"  "/opt/odoo-projects/hellenia/config/production/.env"  "prod"

ls -la "$EVIDENCE_BASE/"
REMOTE

scp -i "$SSH_KEY" -r \
  "${SSH_HOST}:/opt/odoo-projects/hellenia/evidence/accounting-total-audit-readonly/*" \
  "$EVIDENCE_DIR/" 2>/dev/null || true

python3 <<PY
import json, pathlib
ev = pathlib.Path("$EVIDENCE_DIR")
rows = []
for p in sorted(ev.glob("*.json")):
    if p.name.endswith("-skipped.json"):
        d = json.loads(p.read_text())
        rows.append((p.stem.replace("-skipped",""), "SKIP", d.get("reason",""), "-", "-"))
        continue
    try:
        d = json.loads(p.read_text())
    except Exception:
        continue
    if "summary" in d:
        s = d["summary"]
        rows.append((d.get("environment","?"), "PASS" if d.get("pass") else "FINDINGS", s.get("critical_count",0), s.get("high_count",0), len(d.get("errors",[]))))
    else:
        rows.append((p.stem, "FAIL", d.get("error","?"), "-", "-"))

print("\n=== Summary ===")
for r in rows:
    print(f"  {r[0]:6} | {r[1]:8} | critical={r[2]} high={r[3]} errors={r[4]}")
PY

echo "Done. Evidence: $EVIDENCE_DIR"
