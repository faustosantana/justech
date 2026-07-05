#!/usr/bin/env bash
# C1 — Diagnóstico read-only partners sin RNC (solo TEST)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/c1-partners-rnc-diagnostic-test"
SSH_KEY="${HOME}/.ssh/hellenia_vps_ed25519"
SSH_HOST="root@2.25.69.179"
SCRIPT="c1-partners-rnc-diagnostic-test.py"
TS="$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$EVIDENCE_DIR"

scp -i "$SSH_KEY" "${SCRIPT_DIR}/${SCRIPT}" "${SSH_HOST}:/tmp/${SCRIPT}"

ssh -i "$SSH_KEY" "$SSH_HOST" "TS=${TS} SCRIPT=${SCRIPT}" bash -s <<'REMOTE'
set -euo pipefail
PROJECT="/opt/odoo-projects/hellenia"
EVIDENCE="$PROJECT/evidence/c1-partners-rnc-diagnostic-test"
ENV_FILE="$PROJECT/config/test/.env"
IMAGE=hellenia-odoo:19-enterprise
NET=hellenia-test_default
mkdir -p "$EVIDENCE"
source "$ENV_FILE"
DB="${ODOO_DB_NAME:-hellenia_test}"
SCRIPT="${SCRIPT:-c1-partners-rnc-diagnostic-test.py}"

docker run --rm -i --network "$NET" \
  -e HOST=db -e USER="$DB_USER" -e PASSWORD="$DB_PASSWORD" \
  -v hellenia-test_odoo-data:/var/lib/odoo \
  -v "$PROJECT/config/test/odoo.conf:/etc/odoo/odoo.conf:ro" \
  -v "$PROJECT/custom:/opt/odoo/custom:ro" \
  "$IMAGE" odoo shell -d "$DB" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < "/tmp/${SCRIPT}" > "$EVIDENCE/c1-diagnostic-raw.txt" 2>&1

python3 <<PY
import json, pathlib
raw = pathlib.Path("$EVIDENCE/c1-diagnostic-raw.txt").read_text(errors="replace")
marker = "C1_PARTNERS_RNC_DIAGNOSTIC:"
out = pathlib.Path("$EVIDENCE/c1-diagnostic.json")
if marker not in raw:
    print("FAIL: marker not found")
    print(raw[-4000:])
    raise SystemExit(1)
data = json.loads(raw[raw.find(marker)+len(marker):].strip())
data["runner_timestamp"] = "${TS}"
out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
s = data["summary"]
print("partners=", s.get("unique_partners_no_rnc"), "invoices=", s.get("posted_no_rnc_count"), "ncf=", s.get("with_ncf_count"))
PY
REMOTE

scp -i "$SSH_KEY" -r "root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/c1-partners-rnc-diagnostic-test/." "$EVIDENCE_DIR/"

echo "Evidence: $EVIDENCE_DIR"
