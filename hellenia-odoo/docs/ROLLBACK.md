# Rollback — Hellenia Odoo

## DEV / TEST

1. Identificar backup: `ls -lt /opt/odoo-projects/hellenia/backups/dev/`
2. Detener Odoo: `docker compose --env-file config/dev/.env stop odoo`
3. Restaurar PostgreSQL desde `postgres_all.sql.gz`
4. Restaurar filestore desde `filestore.tar.gz`
5. Restaurar addons desde `addons.tar.gz`
6. Reiniciar: `docker compose up -d`

## Producción actual (odoo-pecv)

1. **Siempre** usar backup de `scripts/backup-production-current.sh`
2. Restaurar volúmenes `odoo-pecv_db` y `odoo-pecv_odoo-data`
3. Solo con ventana de mantenimiento aprobada

## Deploy Git rollback

```bash
cd /opt/odoo-projects/hellenia/repository
git checkout <commit-anterior>
/opt/odoo-projects/hellenia/scripts/deploy-test.sh <commit-anterior>
```
