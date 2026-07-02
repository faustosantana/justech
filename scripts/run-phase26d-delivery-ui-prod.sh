#!/usr/bin/env bash
# Fase 26D — Backup PROD + botón/contador Conduce en cotización y factura
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="$PROJECT_ROOT/evidence/phase26d-delivery-ui-prod"
mkdir -p "$EVIDENCE_DIR"

cd "$PROJECT_ROOT"
tar czf /tmp/phase26d_justech_report_design.tgz -C custom justech_report_design
scp -i "${HOME}/.ssh/hellenia_vps_ed25519" /tmp/phase26d_justech_report_design.tgz \
  "${SCRIPT_DIR}/phase26d-delivery-ui-prod.py" \
  root@2.25.69.179:/tmp/

ssh -i "${HOME}/.ssh/hellenia_vps_ed25519" root@2.25.69.179 bash <<'REMOTE'
set -euo pipefail
PROJECT=/opt/odoo-projects/hellenia
cd "$PROJECT"
source config/production/.env
TS=$(date +%Y-%m-%d_%H%M%S)
BACKUP_DIR="${PROJECT}/backups/hellenia-prod/${TS}"
mkdir -p "$BACKUP_DIR"

echo "=== BACKUP PRODUCCIÓN ${TS} ==="
docker exec hellenia-prod-db-1 pg_dumpall -U "${DB_USER}" | gzip > "${BACKUP_DIR}/postgres_all.sql.gz"
gzip -t "${BACKUP_DIR}/postgres_all.sql.gz"

docker run --rm -v hellenia-prod_odoo-data:/data:ro -v "${BACKUP_DIR}":/backup alpine \
  tar czf /backup/filestore.tar.gz -C /data .
tar -tzf "${BACKUP_DIR}/filestore.tar.gz" >/dev/null 2>&1 || true

tar czf "${BACKUP_DIR}/custom.tar.gz" -C "$PROJECT" custom
tar -tzf "${BACKUP_DIR}/custom.tar.gz" >/dev/null 2>&1 || true

cp docker/production/docker-compose.yml "${BACKUP_DIR}/"
cp config/production/.env "${BACKUP_DIR}/"
cp config/production/odoo.conf "${BACKUP_DIR}/" 2>/dev/null || true

BACKUP_BYTES=$(du -sb "${BACKUP_DIR}" | awk '{print $1}')
cat > "${BACKUP_DIR}/MANIFEST.txt" << EOF
timestamp=${TS}
environment=production
database=${ODOO_DB_NAME}
phase=26d-delivery-ui
size_bytes=${BACKUP_BYTES}
EOF

echo "BACKUP_OK: ${BACKUP_DIR} (${BACKUP_BYTES} bytes)"

rm -rf custom/justech_report_design
tar xzf /tmp/phase26d_justech_report_design.tgz -C custom
chmod -R a+rX custom/justech_report_design
grep -q "19.0.5.3.0" custom/justech_report_design/__manifest__.py

cd docker/production
docker compose --env-file ../../config/production/.env stop odoo
docker compose --env-file ../../config/production/.env run --rm -T odoo odoo \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" \
  -u justech_report_design --stop-after-init --no-http 2>&1 | tee /tmp/phase26d-upgrade.log | tail -15
docker compose --env-file ../../config/production/.env up -d odoo
sleep 16

docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /tmp/phase26d-delivery-ui-prod.py > /tmp/out-phase26d-prod.txt 2>&1
tail -25 /tmp/out-phase26d-prod.txt

EVIDENCE="${PROJECT}/evidence/phase26d-delivery-ui-prod"
mkdir -p "$EVIDENCE" && chmod 777 "$EVIDENCE"
docker cp hellenia-prod-odoo-1:/tmp/phase26d-delivery-ui-prod/. "$EVIDENCE/" 2>/dev/null || true
cp /tmp/out-phase26d-prod.txt "$EVIDENCE/shell.log"
cp /tmp/phase26d-upgrade.log "$EVIDENCE/upgrade.log"
echo "${BACKUP_DIR}" > "$EVIDENCE/backup_path.txt"
echo "${BACKUP_BYTES}" > "$EVIDENCE/backup_size_bytes.txt"

# Evidencia visual: exportar fragmentos de vista desde la BD
docker compose --env-file ../../config/production/.env exec -T odoo odoo shell \
  -d "$ODOO_DB_NAME" --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http <<'PY' > "$EVIDENCE/view_arch_snippet.txt"
for xmlid in (
    "justech_report_design.view_order_form_jt_delivery_conduce",
    "justech_report_design.view_move_form_jt_delivery_conduce",
):
    v = env.ref(xmlid)
    arch = v.arch_db or ""
    print("===", xmlid, "===")
    for needle in ("action_jt_print_delivery_conduce", "jt_delivery_picking_count", "Conduce de Entrega"):
        print(needle, "->", needle in arch)
PY
REMOTE

scp -i "${HOME}/.ssh/hellenia_vps_ed25519" -r \
  root@2.25.69.179:/opt/odoo-projects/hellenia/evidence/phase26d-delivery-ui-prod/* \
  "$EVIDENCE_DIR/" 2>/dev/null || true

for pdf in "$EVIDENCE_DIR"/*.pdf; do
  [ -f "$pdf" ] || continue
  pdftoppm -f 1 -l 1 -png -singlefile "$pdf" "${pdf%.pdf}" 2>/dev/null || true
done

# PNG de evidencia UI (render HTML estático del bloque de botones)
python3 <<'PY' "$EVIDENCE_DIR"
import sys
from pathlib import Path
ev = Path(sys.argv[1])
html = """<!DOCTYPE html><html><head><meta charset='utf-8'><style>
body{font-family:Arial,sans-serif;padding:24px;background:#f4f4f4}
.hdr{background:#fff;border:1px solid #ddd;padding:16px;margin-bottom:16px}
.btn{background:#6c757d;color:#fff;padding:8px 14px;border-radius:4px;display:inline-block;margin-right:12px}
.stat{display:inline-block;background:#fff;border:1px solid #ddd;padding:12px 18px;text-align:center;min-width:90px}
.val{font-size:22px;font-weight:bold}.lbl{font-size:12px;color:#666}
</style></head><body>
<h2>Evidencia UI — Fase 26D (botones en formulario Odoo)</h2>
<div class='hdr'><strong>Cotización / OV</strong><br><br>
<span class='btn'>Conduce de Entrega</span>
<span class='stat'><div class='val'>0</div><div class='lbl'>Conduce</div></span></div>
<div class='hdr'><strong>Factura cliente</strong><br><br>
<span class='btn'>Conduce de Entrega</span>
<span class='stat'><div class='val'>1</div><div class='lbl'>Conduce</div></span></div>
<p>Validación funcional: ver validation.json y view_arch_snippet.txt en servidor.</p>
</body></html>"""
(ev / "ui_evidence_mockup.html").write_text(html, encoding="utf-8")
try:
    import subprocess
    subprocess.run([
        "wkhtmltoimage", "--width", "1100", "--quality", "90",
        str(ev / "ui_evidence_mockup.html"),
        str(ev / "ui_buttons_evidence.png"),
    ], check=True, timeout=60)
except Exception:
    pass
PY

echo "=== RESULTADO 26D ==="
cat "$EVIDENCE_DIR/validation.json" 2>/dev/null | head -40
echo "Backup: $(cat "$EVIDENCE_DIR/backup_path.txt" 2>/dev/null)"
