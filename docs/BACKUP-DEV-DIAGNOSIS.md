# Diagnóstico backup DEV — 2026-06-30

## Síntoma

`backup-dev.sh` completaba dump PostgreSQL y filestore, pero terminaba con **exit code 2**.

E1a se detenía en el paso de backup (con `set -euo pipefail` en el pipeline).

## Causa raíz

`scripts/lib/common.sh` → función `hellenia_apply_retention()`:

```bash
ls -1dt "${backup_root}"/20*_weekly 2>/dev/null | tail -n +5 | xargs -r rm -rf
```

Cuando **no existen** backups semanales (`20*_weekly`), GNU `ls` devuelve **código 2** (*no such file*). Con `set -e`, el script aborta **después** de haber creado el backup — falso negativo.

## Corrección

1. **Retención:** usar `shopt -s nullglob` en lugar de `ls` con glob sin coincidencias.
2. **Verificación:** nuevo `verify-backup-dev.sh` — valida artefactos e integridad.
3. **backup-dev.sh:** falla explícitamente si falta algún artefacto requerido; llama a `verify-backup-dev.sh` al final.
4. **e1a-enterprise-image.sh:** si backup o verificación fallan → **DETENIDO** (sin extract, build ni install).

## Artefactos obligatorios por backup DEV

| Archivo | Contenido |
|---------|-----------|
| `postgres_all.sql.gz` | Dump PostgreSQL (`pg_dumpall`) |
| `filestore.tar.gz` | Volumen `hellenia-dev_odoo-data` |
| `docker-compose.yml` | Compose DEV al momento del backup |
| `odoo.conf` | Config DEV |
| `.env` | Variables DEV |
| `custom.tar.gz` | Módulos custom |
| `MANIFEST.txt` | Metadatos auditoría |

## No afectado

- Producción (`odoo-pecv`) — sin cambios
- TEST — sin cambios
