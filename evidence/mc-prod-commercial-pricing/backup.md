# MC-PROD — Backup PROD

**Timestamp:** 2026-07-07_113725  
**Ruta VPS:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/mc-prod-2026-07-07_113725`  
**Base de datos:** `hellenia_prod`  
**Propósito:** Despliegue `justech_multicurrency` v19.0.2.0.0 — precios comerciales USD/DOP

## Contenido

| Archivo | Descripción |
|---------|-------------|
| `hellenia_prod.dump` | pg_dump formato custom (`-Fc`) |
| `filestore.tar.gz` | Filestore Odoo producción |
| `odoo.conf` | Configuración Odoo |
| `env.backup` | Variables entorno (solo en VPS) |
| `MANIFEST.txt` | Metadatos del backup |

## Verificación ejecutada

- `docker exec -i hellenia-prod-db-1 pg_restore -l` sobre el dump — **OK**
- Tamaño dump: **8,512,533 bytes** (~8.1 MB)

## Rollback

Si el despliegue afecta operación:

```bash
source /opt/odoo-projects/hellenia/config/production/.env
BACKUP=/opt/odoo-projects/hellenia/backups/hellenia-prod/mc-prod-2026-07-07_113725

docker exec hellenia-prod-db-1 psql -U "$DB_USER" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='hellenia_prod' AND pid <> pg_backend_pid();"
docker exec hellenia-prod-db-1 psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS hellenia_prod;"
docker exec hellenia-prod-db-1 psql -U "$DB_USER" -d postgres -c "CREATE DATABASE hellenia_prod OWNER \"$DB_USER\";"
docker exec -i hellenia-prod-db-1 pg_restore -U "$DB_USER" -d hellenia_prod --no-owner --role="$DB_USER" \
  < "$BACKUP/hellenia_prod.dump"

cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env restart odoo
```

## Notas

- Backup tomado **antes** de instalar `justech_multicurrency`
- PROD sin operación real ni productos definitivos (autorizado por usuario)
- Segundo backup duplicado en `mc-prod-2026-07-07_113642` (intento previo, descartable)
