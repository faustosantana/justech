# Rollback — DEV-2 erp.justech.do

**Backup:** `/opt/odoo-dev/backups/fiscal-integration-dev2-20260709_215513`

## Cuándo ejecutar

- Fallo en generación 606/607 o corrupción de vistas reports
- Δ inesperado en conteos históricos tras instalar reports
- Error al abrir facturas/pagos/conciliaciones/asientos
- Activación accidental del motor Justech NCF

## Procedimiento

```bash
BACKUP=/opt/odoo-dev/backups/fiscal-integration-dev2-20260709_215513
DB=justech_dev
FS=/opt/odoo-dev/data/filestore/justech_dev

sudo systemctl stop odoo-dev

sudo -u odoo dropdb ${DB}
sudo -u odoo createdb -O odoo ${DB}
sudo -u odoo pg_restore -d ${DB} ${BACKUP}/${DB}.dump

rm -rf ${FS}
mkdir -p ${FS}
tar -xzf ${BACKUP}/filestore_${DB}.tar.gz -C /opt/odoo-dev/data/filestore/

sudo systemctl start odoo-dev
```

## Verificación post-rollback

```bash
sudo -u odoo psql -d justech_dev -t -c "
SELECT COUNT(*) FROM account_move WHERE state='posted';
SELECT COUNT(*) FROM account_move WHERE l10n_latam_document_number IS NOT NULL;
SELECT state FROM ir_module_module WHERE name='justech_l10n_do_reports';
"
# Esperado: 2255 posted, 1504 NCF Adel, reports uninstalled o estado pre-DEV-2
```

## Tiempo estimado

15–25 minutos.
