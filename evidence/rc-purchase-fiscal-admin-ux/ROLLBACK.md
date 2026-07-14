# Rollback — RC-PURCHASE-FISCAL-ADMIN-UX (DEV)

## Entorno
- Solo `erp.justech.do` / BD `justech_dev`
- Producción no modificada

## Backup
- Path: `/root/backups/justech_dev/rc-purchase-fiscal-admin-ux-20260714_202917/`
- `justech_dev.dump` (pg_dump -Fc)
- `filestore/justech_dev_filestore.tgz`
- Módulos previos en `modules/` (si fueron capturados)

## Procedimiento
1. `systemctl stop odoo-dev`
2. Restaurar módulos a versiones previas (19.0.1.24.0 / 19.0.2.8.0 / 19.0.1.8.4) desde git o backup
3. `pg_restore` del dump sobre `justech_dev` (o clonar a DB temporal y validar)
4. `-u justech_l10n_do_base,justech_l10n_do_ncf,justech_fiscal_admin` si se restauró solo código
5. `systemctl start odoo-dev`
6. Validar continuidad B11@11 / B13@213 y GL=0

## Nota
No usar este rollback en Producción sin autorización P0 aparte.
