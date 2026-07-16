# NCF recibido en compras — auditoría y rollback (DEV)

## Entorno
- DEV: erp.justech.do / justech_dev / 207.244.242.58
- Producción: no modificada

## Campo histórico
- NCF recibido: `l10n_latam_document_number` (782/783 facturas proveedor)
- 606 / FDP: lee `justech_do_ncf` y luego `l10n_latam_document_number`
- FP/2026/06/0033: E310000087599 en LATAM

## Causa raíz
- Studio view prio 160 reescribía `invisible` de `l10n_latam_document_number`
  con fórmula Adel que oculta cuando `use_documents=False` y `manual=False`.

## Fix
- Módulo: `justech_l10n_do_ncf` 19.0.2.12.2
- XML ID: `justech_l10n_do_ncf.view_move_form_justech_do_ncf` priority=200
- Ocultar `justech_do_expense_type_suggestion_label`
- Desactivar autocompletado de expense type
- Duplicidad v2.0 incluye LATAM number en compras recibidas

## Rollback
1. Restaurar tarball `/opt/odoo-backups/ncf-vendor-bill-uat-dev-20260716_151010/modules/justech_l10n_do_ncf.tgz`
2. `-u justech_l10n_do_ncf` únicamente
3. No tocar Producción
