# Backup oficial RELEASE 1.0

**Ruta VPS:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/release-1.0-2026-07-07_095537`

## Contenido
- hellenia_prod.dump (PostgreSQL pg_dump -Fc)
- filestore.tar.gz
- custom.tar.gz
- env.backup, odoo.conf, docker-compose.yml

## Verificación
`pg_restore -l hellenia_prod.dump` — OK al generar backup.

Ver ROLLBACK en docs y evidence/coa-prod-adoption/ROLLBACK.md.
