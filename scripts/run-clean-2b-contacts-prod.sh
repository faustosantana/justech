#!/usr/bin/env bash
# CLEAN-2B — Backup + purge remaining commercial/test contacts PROD
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="root@2.25.69.179"
EVIDENCE="$PROJECT_ROOT/evidence/clean-2b-contacts-final"
TS="$(date +%Y-%m-%d_%H%M%S)"
BACKUP="/opt/odoo-projects/hellenia/backups/hellenia-prod/clean-2b-${TS}"
REMOTE_DIR="/opt/odoo-projects/hellenia/custom/clean-2b"

mkdir -p "$EVIDENCE"

echo "=== CLEAN-2B — $TS ==="

ssh -i "$SSH_KEY" "$VPS" "mkdir -p '$REMOTE_DIR'"
scp -i "$SSH_KEY" \
  "$PROJECT_ROOT/scripts/clean-2b-contacts-prod.py" \
  "$PROJECT_ROOT/scripts/clean-2b-contacts-validate-prod.py" \
  "$VPS:$REMOTE_DIR/"

echo "=== Backup CLEAN-2B ==="
ssh -i "$SSH_KEY" "$VPS" "BACKUP='$BACKUP' bash -s" <<REMOTE
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
mkdir -p "\$BACKUP"
docker exec hellenia-prod-db-1 pg_dump -U "\$DB_USER" -Fc hellenia_prod > "\$BACKUP/hellenia_prod.dump"
tar -czf "\$BACKUP/filestore.tar.gz" -C /opt/odoo-projects/hellenia/data/production filestore 2>/dev/null || true
tar -czf "\$BACKUP/custom.tar.gz" -C /opt/odoo-projects/hellenia custom
cp /opt/odoo-projects/hellenia/config/production/.env "\$BACKUP/env.backup"
cp /opt/odoo-projects/hellenia/config/production/odoo.conf "\$BACKUP/odoo.conf"
cp /opt/odoo-projects/hellenia/docker/production/docker-compose.yml "\$BACKUP/docker-compose.yml"
docker exec -i hellenia-prod-db-1 pg_restore -l < "\$BACKUP/hellenia_prod.dump" >/dev/null
echo "BACKUP_OK=\$BACKUP"
ls -lh "\$BACKUP/"
REMOTE

echo "$BACKUP" > "$EVIDENCE/BACKUP_PATH.txt"

echo "=== Ejecutar CLEAN-2B ==="
ssh -i "$SSH_KEY" "$VPS" "REMOTE_DIR='$REMOTE_DIR'" bash -s <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env exec -T odoo bash -lc 'mkdir -p /var/lib/odoo/clean-2b'
docker compose --env-file ../../config/production/.env exec -T \
  -e CLEAN2B_EVIDENCE=/var/lib/odoo/clean-2b \
  odoo odoo shell -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < "$REMOTE_DIR/clean-2b-contacts-prod.py" \
  > "$REMOTE_DIR/clean.log" 2>&1
grep CLEAN2B: "$REMOTE_DIR/clean.log" | tail -1 || { tail -30 "$REMOTE_DIR/clean.log"; exit 1; }

docker compose --env-file ../../config/production/.env exec -T \
  -e CLEAN2B_EVIDENCE=/var/lib/odoo/clean-2b \
  odoo odoo shell -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < "$REMOTE_DIR/clean-2b-contacts-validate-prod.py" \
  > "$REMOTE_DIR/validate.log" 2>&1
grep CLEAN2B_VALIDATE: "$REMOTE_DIR/validate.log" | tail -1 || { tail -30 "$REMOTE_DIR/validate.log"; exit 1; }

/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod > "$REMOTE_DIR/healthcheck.log" 2>&1 || true
tail -8 "$REMOTE_DIR/healthcheck.log"

docker compose --env-file ../../config/production/.env cp odoo:/var/lib/odoo/clean-2b/. "$REMOTE_DIR/evidence/" 2>/dev/null || true
HC=$(ls -t /opt/odoo-projects/hellenia/evidence/healthcheck-prod-*.json 2>/dev/null | head -1)
cp "$HC" "$REMOTE_DIR/healthcheck.json" 2>/dev/null || true
REMOTE

scp -i "$SSH_KEY" -r "$VPS:$REMOTE_DIR/evidence/." "$EVIDENCE/" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:$REMOTE_DIR/healthcheck.json" "$EVIDENCE/healthcheck.json" 2>/dev/null || true
scp -i "$SSH_KEY" "$VPS:$REMOTE_DIR/healthcheck.log" "$EVIDENCE/healthcheck.log" 2>/dev/null || true

python3 <<PY
import json
from pathlib import Path

ev = Path("$EVIDENCE")
backup = Path("$EVIDENCE/BACKUP_PATH.txt").read_text().strip()
report = {}
if (ev / "clean-2b-report.json").exists():
    report = json.loads((ev / "clean-2b-report.json").read_text())
validation = json.loads((ev / "validation.json").read_text()) if (ev / "validation.json").exists() else {}
hc = json.loads((ev / "healthcheck.json").read_text()) if (ev / "healthcheck.json").exists() else {}

(ev / "backup.md").write_text(f"""# CLEAN-2B — Backup pre-limpieza contactos

**Ruta VPS:** \`{backup}\`

## Contenido
- hellenia_prod.dump
- filestore.tar.gz
- custom.tar.gz
- env.backup, odoo.conf, docker-compose.yml

## Verificación
\`pg_restore -l\` — OK
""")

ok = report.get("ok", False) and validation.get("status") == "PASS"
(ev / "SUMMARY.md").write_text(f"""# CLEAN-2B — Limpieza final de contactos

**Resultado:** {'PASS' if ok else 'FAIL'}
**Backup:** \`{backup}\`

## Antes
- Partners totales: {report.get('before', {}).get('partners_total', '?')}
- Visibles (usuario normal, no preservados): {report.get('before', {}).get('visible_non_preserved', '?')}

## Acción
- Eliminados: {report.get('deleted_count', '?')}
- Preservados: {report.get('preserved_count', '?')}

## Después
- Clientes: {validation.get('counts', {}).get('customers', '?')}
- Proveedores: {validation.get('counts', {}).get('suppliers', '?')}
- Visibles no preservados: {validation.get('counts', {}).get('visible_non_preserved', '?')}
- Licencia activa: {validation.get('license', {}).get('active', '?')}
""")
print("Evidence:", ev)
PY

echo "=== CLEAN-2B evidence: $EVIDENCE ==="
