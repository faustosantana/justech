# Rollback — DEV-1 erp.justech.do

**Backup:** `/opt/odoo-dev/backups/fiscal-integration-dev1-20260709_214432`

## Cuándo ejecutar

- Cualquier Δ inesperado en conteos históricos
- Error al abrir facturas/pagos/conciliaciones
- Activación accidental Justech NCF en producción de facturas
- Fallo crítico post-instalación

## Procedimiento (erp.justech.do)

```bash
BACKUP=/opt/odoo-dev/backups/fiscal-integration-dev1-20260709_214432
DB=justech_dev
FS=/opt/odoo-dev/data/filestore/justech_dev

sudo systemctl stop odoo-dev

sudo -u odoo dropdb ${DB}
sudo -u odoo createdb -O odoo ${DB}
sudo -u odoo pg_restore -d ${DB} ${BACKUP}/${DB}.dump

rm -rf ${FS}
mkdir -p ${FS}
tar -xzf ${BACKUP}/filestore_${DB}.tar.gz -C /opt/odoo-dev/data/filestore/

# Opcional: restaurar addons si se modificaron
# tar -xzf ${BACKUP}/custom_addons_justgroup.tar.gz -C /opt/odoo-dev/custom-addons/justgroup/

sudo systemctl start odoo-dev
```

## Verificación post-rollback

```bash
sudo -u odoo psql -d justech_dev -t -c "
SELECT COUNT(*) FROM account_move WHERE state='posted';
SELECT COUNT(*) FROM account_move WHERE l10n_latam_document_number IS NOT NULL;
"
# Esperado: 2255 posted, 1504 NCF Adel
```

## Tiempo estimado

15–25 minutos (incluye stop/start Odoo).
