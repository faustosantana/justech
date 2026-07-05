#!/usr/bin/env bash
# F31.1.1 — Certificación enterprise justech_modules (DEV only)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE="$PROJECT_ROOT/evidence/f31-1-1-license-engine-certification"
mkdir -p "$EVIDENCE"

SSH_KEY="${HOME}/.ssh/hellenia_vps_ed25519"
VPS="root@2.25.69.179"
REMOTE_PROJECT="/opt/odoo-projects/hellenia"
REMOTE_EVIDENCE="$REMOTE_PROJECT/evidence/f31-1-1-license-engine-certification"

echo "=== Sync certification script to VPS ==="
scp -i "$SSH_KEY" "$SCRIPT_DIR/f31-1-1-license-engine-certification.py" "$VPS:/tmp/"

echo "=== Run certification on hellenia_dev ==="
ssh -i "$SSH_KEY" "$VPS" bash <<REMOTE
set -euo pipefail
PROJECT=$REMOTE_PROJECT
source "\$PROJECT/config/dev/.env"
mkdir -p "$REMOTE_EVIDENCE"
LOG="$REMOTE_EVIDENCE/certification_run.log"
docker run --rm --network hellenia-dev_default \
  -e HOST=db -e USER="\$DB_USER" -e PASSWORD="\$DB_PASSWORD" \
  -v hellenia-dev_odoo-data:/var/lib/odoo \
  -v "\$PROJECT/config/dev/odoo.conf:/etc/odoo/odoo.conf:ro" \
  -v "\$PROJECT/custom:/opt/odoo/custom:ro" \
  hellenia-odoo:19-enterprise odoo shell \
  -d hellenia_dev --no-http \
  < /tmp/f31-1-1-license-engine-certification.py 2>&1 | tee "\$LOG"
REMOTE

echo "=== Fetch evidence from VPS ==="
scp -i "$SSH_KEY" -r "$VPS:$REMOTE_EVIDENCE/*" "$EVIDENCE/" 2>/dev/null || true

# Extract JSON marker from log if present
python3 <<'PY'
import json
import re
from pathlib import Path

evidence = Path("$EVIDENCE")
log = evidence / "certification_run.log"
if log.exists():
    text = log.read_text()
    m = re.search(r"F31_1_1:(\{.*\})\s*$", text, re.DOTALL | re.MULTILINE)
    if not m:
        # try last line with marker
        for line in reversed(text.splitlines()):
            if line.startswith("F31_1_1:"):
                payload = line[len("F31_1_1:"):]
                out = evidence / "certification-results.json"
                out.write_text(payload)
                print(f"Extracted → {out}")
                break
    else:
        out = evidence / "certification-results.json"
        out.write_text(m.group(1))
        print(f"Extracted → {out}")
PY

echo "=== Done. Evidence in $EVIDENCE ==="
