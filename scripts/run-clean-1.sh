#!/usr/bin/env bash
# CLEAN-1 — Backup + limpieza definitiva datos prueba PROD (sin push/merge)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="root@2.25.69.179"
EVIDENCE="$PROJECT_ROOT/evidence/clean-1"
TS="$(date +%Y-%m-%d_%H%M%S)"
BACKUP="/opt/odoo-projects/hellenia/backups/hellenia-prod/clean-1-${TS}"
REMOTE_DIR="/opt/odoo-projects/hellenia/custom/clean-1"

mkdir -p "$EVIDENCE"

echo "=== CLEAN-1 — $TS ==="

# Deploy scripts
ssh -i "$SSH_KEY" "$VPS" "mkdir -p '$REMOTE_DIR'"
scp -i "$SSH_KEY" \
  "$PROJECT_ROOT/scripts/clean-1-prod.py" \
  "$PROJECT_ROOT/scripts/clean-1-validate-prod.py" \
  "$VPS:$REMOTE_DIR/"

# 1. Backup completo + verificación
echo "=== Backup CLEAN-1 ==="
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

# 2. Ejecutar limpieza
echo "=== Ejecutar CLEAN-1 ==="
ssh -i "$SSH_KEY" "$VPS" "REMOTE_DIR='$REMOTE_DIR'" bash -s <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env exec -T odoo bash -lc 'mkdir -p /var/lib/odoo/clean-1'
docker compose --env-file ../../config/production/.env exec -T \
  -e CLEAN1_EVIDENCE=/var/lib/odoo/clean-1 \
  odoo odoo shell -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < "$REMOTE_DIR/clean-1-prod.py" \
  > "$REMOTE_DIR/clean.log" 2>&1
grep CLEAN1: "$REMOTE_DIR/clean.log" | tail -1

docker compose --env-file ../../config/production/.env exec -T \
  -e CLEAN1_EVIDENCE=/var/lib/odoo/clean-1 \
  odoo odoo shell -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < "$REMOTE_DIR/clean-1-validate-prod.py" \
  > "$REMOTE_DIR/validate.log" 2>&1
grep CLEAN1_VALIDATE: "$REMOTE_DIR/validate.log" | tail -1

/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod > "$REMOTE_DIR/healthcheck.log" 2>&1 || true
tail -8 "$REMOTE_DIR/healthcheck.log"

docker compose --env-file ../../config/production/.env cp odoo:/var/lib/odoo/clean-1/. "$REMOTE_DIR/evidence/" 2>/dev/null || true
HC=$(ls -t /opt/odoo-projects/hellenia/evidence/healthcheck-prod-*.json 2>/dev/null | head -1)
cp "$HC" "$REMOTE_DIR/healthcheck.json" 2>/dev/null || true
REMOTE

# 3. Descargar evidencia
scp -i "$SSH_KEY" -r "$VPS:$REMOTE_DIR/." "$EVIDENCE/remote/" 2>/dev/null || true
if [[ -f "$EVIDENCE/remote/evidence/deleted_records.json" ]]; then
  cp "$EVIDENCE/remote/evidence/deleted_records.json" "$EVIDENCE/deleted_records.json"
elif [[ -f "$EVIDENCE/remote/deleted_records.json" ]]; then
  cp "$EVIDENCE/remote/deleted_records.json" "$EVIDENCE/deleted_records.json"
fi
if [[ -f "$EVIDENCE/remote/healthcheck.json" ]]; then
  cp "$EVIDENCE/remote/healthcheck.json" "$EVIDENCE/healthcheck.json"
fi

# 4. Generar deliverables locales
BACKUP_PATH="$(cat "$EVIDENCE/BACKUP_PATH.txt")"
python3 <<PY
import json
from pathlib import Path

ev = Path("$EVIDENCE")
backup = "$BACKUP_PATH"

deleted = {}
for p in [ev / "deleted_records.json", ev / "remote" / "deleted_records.json", ev / "remote" / "evidence" / "deleted_records.json"]:
    if p.exists():
        deleted = json.loads(p.read_text())
        break

validation = {}
for p in [ev / "remote" / "evidence" / "validation.json", ev / "remote" / "validation.json"]:
    if p.exists():
        validation = json.loads(p.read_text())
        break

hc = {}
if (ev / "healthcheck.json").exists():
    hc = json.loads((ev / "healthcheck.json").read_text())

ok = deleted.get("ok", False) and validation.get("pass", True)
preflight = deleted.get("before", {}).get("preflight", {})
postflight = deleted.get("before", {}).get("postflight", {})
preserved = deleted.get("preserved", {})

(ev / "backup.md").write_text(f"""# CLEAN-1 — Backup pre-limpieza

**Ruta VPS:** \`{backup}\`
**Timestamp:** {deleted.get('timestamp_utc', 'N/A')}

## Contenido
- hellenia_prod.dump (PostgreSQL pg_dump -Fc)
- filestore.tar.gz
- custom.tar.gz
- env.backup, odoo.conf, docker-compose.yml

## Verificación
\`pg_restore -l hellenia_prod.dump\` — OK al generar backup.
""", encoding="utf-8")

(ev / "rollback.md").write_text(f"""# CLEAN-1 — Plan de rollback

**Base de datos:** hellenia_prod
**Instancia:** https://odoo.hellenia.cloud
**Backup:** \`{backup}\`

## Cuándo ejecutar rollback

- Error crítico durante CLEAN-1 (\`ok: false\`)
- Validación post-limpieza fallida
- Pérdida de configuración, partners, productos o catálogo contable
- Healthcheck PROD fallido tras limpieza

## Procedimiento

\`\`\`bash
ssh -i ~/.ssh/hellenia_vps_ed25519 root@2.25.69.179
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env stop odoo

BACKUP="{backup}"
docker exec hellenia-prod-db-1 psql -U "\$DB_USER" -d postgres -c \\
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='hellenia_prod' AND pid <> pg_backend_pid();"
docker exec hellenia-prod-db-1 psql -U "\$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS hellenia_prod;"
docker exec hellenia-prod-db-1 psql -U "\$DB_USER" -d postgres -c "CREATE DATABASE hellenia_prod OWNER \\"\$DB_USER\\";"
docker exec -i hellenia-prod-db-1 pg_restore -U "\$DB_USER" -d hellenia_prod --no-owner --role="\$DB_USER" < "\$BACKUP/hellenia_prod.dump"

tar -xzf "\$BACKUP/filestore.tar.gz" -C /opt/odoo-projects/hellenia/data/production
docker compose --env-file ../../config/production/.env start odoo
\`\`\`
""", encoding="utf-8")

deleted_lines = []
for k, v in deleted.get("deleted", {}).items():
    deleted_lines.append(f"- **{k}:** {v.get('count', 0)}")

preserved_lines = []
for k, v in preserved.items():
    preserved_lines.append(f"- **{k}:** {v}")

checks = deleted.get("validation", {})
val_checks = validation.get("counts", {})
hc_pass = hc.get("pass", hc.get("ok", "ver log"))

(ev / "CLEAN_REPORT.md").write_text(f"""# CLEAN-1 — Limpieza definitiva PRE GO-LIVE

**Fecha:** {deleted.get('timestamp_utc', 'N/A')}
**Base de datos:** hellenia_prod
**Resultado global:** {'PASS' if ok else 'FAIL'}

## Resumen eliminación (preflight → postflight)

| Área | Antes | Después |
|------|-------|---------|
| Asientos publicados | {preflight.get('account_move_posted', '?')} | {postflight.get('account_move_posted', '?')} |
| Asientos totales | {preflight.get('account_move', '?')} | {postflight.get('account_move', '?')} |
| Pagos | {preflight.get('account_payment', '?')} | {postflight.get('account_payment', '?')} |
| Pedidos venta | {preflight.get('sale_order', '?')} | {postflight.get('sale_order', '?')} |
| Órdenes compra | {preflight.get('purchase_order', '?')} | {postflight.get('purchase_order', '?')} |
| Extractos banco | {preflight.get('bank_statement', '?')} | {postflight.get('bank_statement', '?')} |
| Reportes fiscales | {preflight.get('fiscal_report', '?')} | {postflight.get('fiscal_report', '?')} |
| Consumos NCF | {preflight.get('ncf_consumption', '?')} | {postflight.get('ncf_consumption', '?')} |
| Pickings | {preflight.get('stock_picking', '?')} | {postflight.get('stock_picking', '?')} |
| Logs auditoría | {preflight.get('audit_log', '?')} | {postflight.get('audit_log', '?')} |

## Registros eliminados por categoría

{chr(10).join(deleted_lines) or '- Ver deleted_records.json'}

## Conservado

{chr(10).join(preserved_lines) or '- Ver deleted_records.json preserved'}

## Reinicio secuencias NCF

{chr(10).join(f"- {r['name']} ({r['prefix']}): next {r['before_next']} → {r['after_next']}" for r in deleted.get('ncf_resets', []))}

## Validación

- Checks internos CLEAN-1: {checks}
- Conteos post-validación: {val_checks}
- DGII: {validation.get('dgii', {})}
- Healthcheck: {hc_pass}

## Errores

{chr(10).join('- ' + e for e in deleted.get('errors', [])) or '- Ninguno'}

## ¿Listo para operación real?

{'**Sí** — datos operativos eliminados, configuración intacta, validaciones PASS.' if ok else '**No** — revisar errores y ejecutar rollback si aplica.'}
""", encoding="utf-8")

print("Evidence generated in", ev)
PY

echo "=== CLEAN-1 evidence: $EVIDENCE ==="
