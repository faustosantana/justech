# CLEAN-1 — Backup pre-limpieza

**Ruta VPS:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/clean-1-2026-07-07_103112`  
**Timestamp:** 2026-07-07 14:31 UTC

## Contenido

- `hellenia_prod.dump` — PostgreSQL pg_dump -Fc (8.2 MB)
- `filestore.tar.gz`
- `custom.tar.gz`
- `env.backup`, `odoo.conf`, `docker-compose.yml`

## Verificación

```bash
BACKUP="/opt/odoo-projects/hellenia/backups/hellenia-prod/clean-1-2026-07-07_103112"
docker exec -i hellenia-prod-db-1 pg_restore -l < "$BACKUP/hellenia_prod.dump" >/dev/null && echo "DUMP OK"
```

**Estado:** verificado OK al generar backup (pre-ejecución CLEAN-1).
