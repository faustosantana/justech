# CLEAN-1 — Plan de rollback

**Base de datos:** `hellenia_prod`  
**Instancia:** https://odoo.hellenia.cloud  
**VPS:** `root@2.25.69.179`  
**Backup:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/clean-1-2026-07-07_103112`

## Cuándo ejecutar rollback

- Error crítico durante CLEAN-1
- Pérdida de configuración, partners, productos o catálogo contable
- Validación post-limpieza fallida
- Healthcheck PROD fallido tras limpieza

## Procedimiento de restore

```bash
ssh -i ~/.ssh/hellenia_vps_ed25519 root@2.25.69.179
source /opt/odoo-projects/hellenia/config/production/.env
cd /opt/odoo-projects/hellenia/docker/production
docker compose --env-file ../../config/production/.env stop odoo

BACKUP="/opt/odoo-projects/hellenia/backups/hellenia-prod/clean-1-2026-07-07_103112"

docker exec hellenia-prod-db-1 psql -U "$DB_USER" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='hellenia_prod' AND pid <> pg_backend_pid();"
docker exec hellenia-prod-db-1 psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS hellenia_prod;"
docker exec hellenia-prod-db-1 psql -U "$DB_USER" -d postgres -c "CREATE DATABASE hellenia_prod OWNER \"$DB_USER\";"
docker exec -i hellenia-prod-db-1 pg_restore -U "$DB_USER" -d hellenia_prod --no-owner --role="$DB_USER" \
  < "$BACKUP/hellenia_prod.dump"

tar -xzf "$BACKUP/filestore.tar.gz" -C /opt/odoo-projects/hellenia/data/production
docker compose --env-file ../../config/production/.env start odoo
```

## Verificación post-restore

```bash
/opt/odoo-projects/hellenia/scripts/healthcheck.sh prod
```
