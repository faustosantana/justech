# Dependency Graph (Odoo + Commercial)
## hellenia_account
- Odoo depends: hellenia_base, account, justech_l10n_do_base, justech_l10n_do_ncf, l10n_do_check_printing
- Commercial deps: hellenia_base, justech_l10n_do_base, justech_l10n_do_ncf
- Features: hellenia_account

## hellenia_base
- Odoo depends: base
- Commercial deps: —
- Features: hellenia_base

## hellenia_inventory
- Odoo depends: hellenia_base, stock
- Commercial deps: hellenia_base
- Features: hellenia_inventory

## hellenia_pos
- Odoo depends: hellenia_base, point_of_sale
- Commercial deps: hellenia_base
- Features: hellenia_pos

## hellenia_reports
- Odoo depends: hellenia_base, hellenia_account, sale, account, purchase, stock, justech_l10n_do_ncf, account_reports, account_followup
- Commercial deps: hellenia_account, justech_l10n_do_ncf
- Features: hellenia_reports

## hellenia_ui
- Odoo depends: base, sale_management, purchase, stock, account, contacts, stock_barcode
- Commercial deps: hellenia_base
- Features: hellenia_ui

## hellenia_ux
- Odoo depends: hellenia_ui, hellenia_account, hellenia_reports, justech_l10n_do_ncf, justech_l10n_do_base, justech_l10n_do_reports, sale_management, purchase, stock
- Commercial deps: hellenia_ui, hellenia_account
- Features: hellenia_ux

## justech_core
- Odoo depends: base
- Commercial deps: —
- Features: justech_core

## justech_l10n_do_base
- Odoo depends: account, contacts, l10n_do
- Commercial deps: —
- Features: l10n_do_base

## justech_l10n_do_ncf
- Odoo depends: justech_l10n_do_base, account_debit_note, sale
- Commercial deps: justech_l10n_do_base
- Features: l10n_do_ncf

## justech_l10n_do_reports
- Odoo depends: justech_l10n_do_ncf, hellenia_account
- Commercial deps: justech_l10n_do_ncf
- Features: l10n_do_reports

## justech_modules
- Odoo depends: base, mail
- Commercial deps: —
- Features: platform_core

## justech_report_design
- Odoo depends: mail, sale, sale_stock, stock, account, purchase, portal, hellenia_reports
- Commercial deps: hellenia_reports
- Features: justech_report_design

