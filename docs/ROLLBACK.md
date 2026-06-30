# Rollback — Hellenia Odoo

## DEV / TEST (automatizado)

```bash
# Listar backups
ls -lt /opt/odoo-projects/hellenia/backups/dev/

# Restaurar DEV
/opt/odoo-projects/hellenia/scripts/restore-dev.sh \
  /opt/odoo-projects/hellenia/backups/dev/<TIMESTAMP>

# Restaurar TEST
/opt/odoo-projects/hellenia/scripts/restore-test.sh \
  /opt/odoo-projects/hellenia/backups/test/<TIMESTAMP>
```

Cada script crea backup de seguridad antes de restaurar.

### Restauración manual (si scripts no disponibles)

1. Detener Odoo: `docker compose --env-file config/dev/.env stop odoo`
2. Restaurar PostgreSQL desde `postgres_all.sql.gz`
3. Restaurar filestore desde `filestore.tar.gz`
4. Restaurar addons desde `custom.tar.gz`
5. Reiniciar: `docker compose up -d`

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

## Rollback E1 (Enterprise)

Ver [E1-CHECKLIST.md](E1-CHECKLIST.md) Parte E.
