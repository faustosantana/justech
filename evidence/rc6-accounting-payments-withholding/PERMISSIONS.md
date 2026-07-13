# Permisos catálogo `justech.do.withholding.catalog`

| Grupo | R | W | C | U |
|-------|---|---|---|---|
| account.group_account_invoice | 1 | 0 | 0 | 0 |
| justech_l10n_do_base.group_justech_do_fiscal_user | 1 | 0 | 0 | 0 |
| justech_l10n_do_base.group_justech_do_fiscal_manager | 1 | 0 | 0 | 0 |
| justech_l10n_do_payments_withholding.group_justech_withholding_catalog_admin | 1 | 1 | 1 | 1 |
| account.group_account_manager | 1 | 1 | 1 | 1 |

Record rule: `['|', ('company_id','=',False), ('company_id','in', company_ids)]`

Puente post-init/migrate: Administrador Fiscal e Account Manager implican Administrador de Retenciones.
