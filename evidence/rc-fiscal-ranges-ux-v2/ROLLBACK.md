# Rollback DEV — RC-FISCAL-RANGES-UX-V2

Backup: `/root/backups/justech_dev/rc-fiscal-ranges-ux-v2-20260714_211756/`
1. systemctl stop odoo-dev
2. Restaurar módulos desde backup/modules o git checkout previo
3. pg_restore dump si se requiere BD previa
4. -u justech_l10n_do_ncf,justech_l10n_do_reports,justech_fiscal_admin
5. systemctl start odoo-dev

No aplica a Producción sin autorización P0.
