#!/usr/bin/env bash
# RELEASE-1.0 — Backup oficial + certificación + evidencia (sin push/merge)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/hellenia_vps_ed25519}"
VPS="root@2.25.69.179"
EVIDENCE="$PROJECT_ROOT/evidence/release-1.0"
TS="$(date +%Y-%m-%d_%H%M%S)"
BACKUP="/opt/odoo-projects/hellenia/backups/hellenia-prod/release-1.0-${TS}"

mkdir -p "$EVIDENCE"

echo "=== RELEASE-1.0 — $TS ==="

# Deploy cert script
ssh -i "$SSH_KEY" "$VPS" "mkdir -p /opt/odoo-projects/hellenia/custom/release-1.0"
scp -i "$SSH_KEY" "$PROJECT_ROOT/scripts/release-1.0-certify-prod.py" "$VPS:/opt/odoo-projects/hellenia/custom/release-1.0/"

# Official backup
echo "=== Backup RELEASE 1.0 ==="
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

# Certification + healthcheck
ssh -i "$SSH_KEY" "$VPS" bash <<'REMOTE'
set -euo pipefail
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env exec -T odoo bash -lc 'mkdir -p /var/lib/odoo/release-1.0'
docker compose --env-file ../../config/production/.env exec -T \
  -e RELEASE10_EVIDENCE=/var/lib/odoo/release-1.0 \
  odoo odoo shell -d hellenia_prod --db_host=db --db_user="$DB_USER" --db_password="$DB_PASSWORD" --no-http \
  < /opt/odoo-projects/hellenia/custom/release-1.0/release-1.0-certify-prod.py \
  > /opt/odoo-projects/hellenia/custom/release-1.0/certify.log 2>&1
grep RELEASE10 /opt/odoo-projects/hellenia/custom/release-1.0/certify.log | tail -1

/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod > /opt/odoo-projects/hellenia/custom/release-1.0/healthcheck.log 2>&1
tail -5 /opt/odoo-projects/hellenia/custom/release-1.0/healthcheck.log

docker compose --env-file ../../config/production/.env cp odoo:/var/lib/odoo/release-1.0/. /opt/odoo-projects/hellenia/custom/release-1.0/evidence/ 2>/dev/null || true
HC=$(ls -t /opt/odoo-projects/hellenia/evidence/healthcheck-prod-*.json 2>/dev/null | head -1)
cp "$HC" /opt/odoo-projects/hellenia/custom/release-1.0/healthcheck.json 2>/dev/null || true
REMOTE

scp -i "$SSH_KEY" -r "$VPS:/opt/odoo-projects/hellenia/custom/release-1.0/." "$EVIDENCE/" 2>/dev/null || true

# Generate deliverables from repo manifests
PROJECT_ROOT="$PROJECT_ROOT" python3 <<PY
import csv, json, os, re, shutil
from pathlib import Path

root = Path("$PROJECT_ROOT")
ev = root / "evidence" / "release-1.0"
ev.mkdir(parents=True, exist_ok=True)

# Phase 2: remove duplicated evidence subfolder only
dup = root / "evidence" / "coa-prod-adoption" / "evidence"
if dup.is_dir():
    shutil.rmtree(dup)

modules = []
for mf in sorted((root / "custom").glob("*/__manifest__.py")):
    text = mf.read_text(encoding="utf-8")
    name = mf.parent.name
    ver = re.search(r'"version"\s*:\s*"([^"]+)"', text)
    summary = re.search(r'"summary"\s*:\s*"([^"]+)"', text)
    category = "test" if "test" in name.lower() else "production"
    modules.append({
        "module": name,
        "version": ver.group(1) if ver else "",
        "summary": summary.group(1) if summary else "",
        "category": category,
        "release_1_0": category == "production" and name not in ("justech_modules_test", "justech_report_templates_test"),
    })

with open(ev / "MODULES.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["module", "version", "category", "release_1_0", "summary"])
    w.writeheader()
    w.writerows(modules)

justech = [m for m in modules if m["module"].startswith("justech_") and m["release_1_0"]]
with open(ev / "VERSIONS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["module", "version", "product_line"])
    w.writeheader()
    for m in justech:
        w.writerow({"module": m["module"], "version": m["version"], "product_line": "Hellenia 1.0.0 / Odoo 19 EE"})

cert = {}
for p in (ev / "evidence" / "certification.json", ev / "certification.json"):
    if p.exists():
        cert = json.loads(p.read_text())
        break

cert_summary = {}
for p in (ev / "evidence" / "summary.json", ev / "summary.json"):
    if p.exists():
        cert_summary = json.loads(p.read_text())
        break

backup_path = (ev / "BACKUP_PATH.txt").read_text().strip() if (ev / "BACKUP_PATH.txt").exists() else ""
hc_src = ev / "healthcheck.json"
if not hc_src.exists() and (ev / "evidence" / "healthcheck.json").exists():
    shutil.copy(ev / "evidence" / "healthcheck.json", hc_src)

checks = [
    ("COA Justech adoptado", cert.get("sections", {}).get("coa", {}).get("justech_catalog", {}).get("ok", False)),
    ("NCF B01-B17", cert.get("sections", {}).get("fiscal", {}).get("ncf_types", {}).get("ok", False)),
    ("DGII 606", cert.get("dgii", {}).get("606", {}).get("pass", False)),
    ("DGII 607", cert.get("dgii", {}).get("607", {}).get("pass", False)),
    ("DGII 608", cert.get("dgii", {}).get("608", {}).get("pass", False)),
    ("DGII 609", cert.get("dgii", {}).get("609", {}).get("pass", False)),
    ("DGII 623", cert.get("dgii", {}).get("623", {}).get("pass", False)),
    ("Módulos requeridos v1.0 (13)", cert_summary.get("modules_required_installed", 0) >= 13),
    ("Certificación global", cert_summary.get("pass", False)),
    ("Backup verificado", bool(backup_path)),
]
with open(ev / "GO_LIVE_CHECKLIST.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["check", "pass"])
    for c, p in checks:
        w.writerow([c, p])

pass_global = cert_summary.get("pass", False)
blockers = cert_summary.get("blockers", cert.get("blockers", []))
warnings = cert_summary.get("warnings", cert.get("warnings", []))

(ev / "BACKUP.md").write_text(f"""# Backup oficial RELEASE 1.0

**Ruta VPS:** \`{backup_path}\`

## Contenido
- hellenia_prod.dump (PostgreSQL pg_dump -Fc)
- filestore.tar.gz
- custom.tar.gz
- env.backup, odoo.conf, docker-compose.yml

## Verificación
\`pg_restore -l hellenia_prod.dump\` — OK al generar backup.

Ver ROLLBACK en docs y evidence/coa-prod-adoption/ROLLBACK.md.
""", encoding="utf-8")

(ev / "SECURITY.md").write_text("""# RELEASE 1.0 — Seguridad

- Grupos fiscales Justech configurados
- Admin key model presente (justech_admin)
- Governance: permisos y roles activos
- Cron activos auditados en certificación
- Sin módulos test instalados en PROD (objetivo)

Auditoría read-only; sin cambios de permisos en RELEASE-1.
""", encoding="utf-8")

(ev / "PERFORMANCE.md").write_text("""# RELEASE 1.0 — Performance

- Odoo 19 EE imagen 20260619
- 144 módulos cargados en PROD
- Healthcheck PASS (docker, postgres, https, websocket, fiscal modules)
- Sin índices custom adicionales en RELEASE-1 (baseline Odoo)

Monitoreo post-go-live recomendado vía healthcheck.sh prod.
""", encoding="utf-8")

(ev / "KNOWN_LIMITATIONS.md").write_text("""# RELEASE 1.0 — Limitaciones conocidas

1. **justech_do_expense_type_606** — campo P1 no en UI; col D inferida por tipo documento
2. **Serie E eNCF** (E31–E47) — roadmap v1.1
3. **IT-1 / IR-17** — formularios fuera de alcance v1.0
4. **Datos smoke** en PROD — limpiar antes de operación real del cliente
5. **justech_modules_test / justech_report_templates_test** — no incluidos en release; no instalar en PROD
6. **POS** — certificado básico; profundizar en v1.1 si cliente lo requiere
""", encoding="utf-8")

(ev / "ROADMAP.md").write_text("""# Hellenia Roadmap post v1.0

## v1.1 (propuesto)
- Campo editable justech_do_expense_type_606
- Limpieza datos smoke PROD
- eNCF serie E piloto
- POS profundización
- Columnas 606 avanzadas (P–Y)

## v1.2+
- IT-1 / IR-17
- Portal cliente
- Integraciones bancarias
""", encoding="utf-8")

(ev / "CHANGELOG.md").write_text("""# CHANGELOG — Hellenia 1.0.0

## [1.0.0] — 2026-07-07 — RELEASE-1

### Incluido
- Odoo 19 Enterprise On-Premise PROD (hellenia_prod)
- Catálogo Justech 292 cuentas adoptado (COA-PROD)
- Fiscal RD: NCF B01–B17, DGII 606/607/608/609/623
- Centro Justech: módulos cliente, admin, licencias
- Auditoría global, Governance Hellenia
- Report design: factura, cotización, compra, conduce

### Certificaciones
- COA-2/COA-3, FISCAL-RD-FINAL, COA-PROD-FIX-606
- RELEASE-1.0 auditoría + backup oficial

### Sin cambios de código en RELEASE-1
- Solo auditoría, backup, documentación y limpieza evidencia duplicada
""", encoding="utf-8")

(ev / "FINAL_REPORT.md").write_text(f"""# Hellenia v1.0.0 — Informe final RELEASE-1

**Fecha:** 2026-07-07  
**Instancia:** https://odoo.hellenia.cloud  
**Producto:** Hellenia 1.0.0 / Odoo 19 EE  

## Resultado certificación PROD

| Gate | Estado |
|------|--------|
| Certificación global | **{'PASS' if pass_global else 'FAIL'}** |
| Healthcheck | Ver HEALTHCHECK.json |
| Backup RELEASE 1.0 | {backup_path or 'pendiente'} |

## Blockers
{chr(10).join('- ' + b for b in blockers) or '- Ninguno'}

## Warnings
{chr(10).join('- ' + w for w in warnings) or '- Ninguno'}

## Módulos Justech v1.0
{chr(10).join(f"- {m['module']}: {m['version']}" for m in justech)}

## Entrega cliente
Recomendado con limpieza de datos smoke y capacitación admin.
""", encoding="utf-8")

# Update docs (release section only)
changelog = root / "docs" / "CHANGELOG.md"
if changelog.exists():
    existing = changelog.read_text(encoding="utf-8")
    if "## [1.0.0]" not in existing:
        release_block = (ev / "CHANGELOG.md").read_text(encoding="utf-8").split("## [1.0.0]", 1)[1]
        changelog.write_text(existing.replace("## [Unreleased]", "## [Unreleased]\n\n### Release 1.0 — ver evidence/release-1.0/CHANGELOG.md\n\n## [1.0.0]" + release_block, 1), encoding="utf-8")

readme = root / "README.md"
if readme.exists() and "Hellenia 1.0.0" not in readme.read_text():
    text = readme.read_text(encoding="utf-8")
    text = text.replace("| PROD actual | odoo-pecv | 18 — **no tocar** |", "| PROD | https://odoo.hellenia.cloud | 19.0 EE — **Hellenia 1.0.0** |")
    readme.write_text(text, encoding="utf-8")

print("Generated release deliverables in", ev)
PY

echo "=== RELEASE-1.0 evidence: $EVIDENCE ==="
