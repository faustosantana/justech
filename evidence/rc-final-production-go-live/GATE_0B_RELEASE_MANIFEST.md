# GATE 0B — Release Manifest

- **Hash:** ver objeto git de este commit (`git rev-parse HEAD`); tag anotado `rc/gate0b-justech-production-candidate`
- **Rama:** `feature/fiscal-standard-consolidation`
- **Fecha (UTC):** 2026-07-14 05:27:30Z
- **Entorno validación:** erp.justech.do / justech_dev
- **Producción:** no modificada

## Módulos y versiones

| Módulo | Versión |
|---|---|
| `justech_admin_center` | `19.0.2.11.6` |
| `justech_fiscal_admin` | `19.0.1.8.4` |
| `justech_l10n_do_treasury` | `19.0.1.6.2` |
| `justech_l10n_do_reports` | `19.0.1.24.3` |
| `justech_warranty` | `19.0.1.9.0` |
| `justech_recurring_fee` | `19.0.1.0.2` |
| `justech_ecf_admin` | `19.0.1.3.0` |
| `justech_ecf_core` | `19.0.1.2.1` |
| `justech_ecf_dgii` | `19.0.1.0.0` |
| `justech_global_audit_log` | `19.0.4.1.4` |
| `justech_modules` | `19.0.1.8.7` |

## Archivos incluidos (112 + este manifiesto)

- `custom/justech_admin_center/__init__.py`
- `custom/justech_admin_center/__manifest__.py`
- `custom/justech_admin_center/controllers/__init__.py`
- `custom/justech_admin_center/controllers/main.py`
- `custom/justech_admin_center/models/justech_admin_console.py`
- `custom/justech_admin_center/models/justech_admin_health_finding.py`
- `custom/justech_admin_center/models/justech_admin_health_service.py`
- `custom/justech_admin_center/models/justech_admin_module_company.py`
- `custom/justech_admin_center/models/justech_admin_product.py`
- `custom/justech_admin_center/models/res_users.py`
- `custom/justech_admin_center/static/description/icon.png`
- `custom/justech_admin_center/views/justech_admin_console_views.xml`
- `custom/justech_admin_center/views/justech_admin_hub_views.xml`
- `custom/justech_admin_center/views/menu.xml`
- `custom/justech_admin_center/wizards/admin_auth_wizard_views.xml`
- `custom/justech_admin_center/wizards/role_assign_wizard_views.xml`
- `custom/justech_ecf_admin/CHANGELOG.md`
- `custom/justech_ecf_admin/__manifest__.py`
- `custom/justech_ecf_admin/models/ecf_admin_hub.py`
- `custom/justech_ecf_admin/models/ecf_api_token.py`
- `custom/justech_ecf_admin/security/ecf_role_bridge.xml`
- `custom/justech_ecf_admin/security/ir.model.access.csv`
- `custom/justech_ecf_admin/wizards/ecf_setup_wizard.py`
- `custom/justech_ecf_core/__manifest__.py`
- `custom/justech_ecf_core/models/ecf_certificate.py`
- `custom/justech_ecf_core/models/ecf_company_config.py`
- `custom/justech_ecf_dgii/models/dgii_client.py`
- `custom/justech_fiscal_admin/__manifest__.py`
- `custom/justech_fiscal_admin/models/justech_fiscal_admin_center.py`
- `custom/justech_fiscal_admin/models/res_users.py`
- `custom/justech_fiscal_admin/static/src/scss/fiscal_admin.scss`
- `custom/justech_fiscal_admin/views/justech_fiscal_admin_center_views.xml`
- `custom/justech_fiscal_admin/views/justech_res_config_settings_views.xml`
- `custom/justech_global_audit_log/models/audit_log.py`
- `custom/justech_l10n_do_reports/__manifest__.py`
- `custom/justech_l10n_do_reports/models/dgii_fiscal_workflow.py`
- `custom/justech_l10n_do_reports/models/dgii_report_review.py`
- `custom/justech_l10n_do_reports/views/dgii_report_review_views.xml`
- `custom/justech_l10n_do_treasury/__manifest__.py`
- `custom/justech_l10n_do_treasury/models/account_payment.py`
- `custom/justech_l10n_do_treasury/views/account_payment_open_views.xml`
- `custom/justech_l10n_do_treasury/views/menu_accounting_navigation.xml`
- `custom/justech_modules/models/justech_license_service.py`
- `custom/justech_recurring_fee/CHANGELOG.md`
- `custom/justech_recurring_fee/__manifest__.py`
- `custom/justech_recurring_fee/models/account_move.py`
- `custom/justech_recurring_fee/models/recurring_fee.py`
- `custom/justech_recurring_fee/models/recurring_fee_cycle.py`
- `custom/justech_recurring_fee/models/recurring_fee_line.py`
- `custom/justech_recurring_fee/models/sale_order.py`
- `custom/justech_recurring_fee/views/account_move_views.xml`
- `custom/justech_recurring_fee/views/recurring_fee_views.xml`
- `custom/justech_recurring_fee/views/sale_order_views.xml`
- `custom/justech_warranty/CHANGELOG.md`
- `custom/justech_warranty/LICENSE`
- `custom/justech_warranty/README.md`
- `custom/justech_warranty/__init__.py`
- `custom/justech_warranty/__manifest__.py`
- `custom/justech_warranty/controllers/__init__.py`
- `custom/justech_warranty/data/.gitkeep`
- `custom/justech_warranty/data/ir_sequence.xml`
- `custom/justech_warranty/data/warranty_config_data.xml`
- `custom/justech_warranty/data/warranty_cron.xml`
- `custom/justech_warranty/docs/FUNCIONAL.md`
- `custom/justech_warranty/docs/TECNICO.md`
- `custom/justech_warranty/i18n/.gitkeep`
- `custom/justech_warranty/models/__init__.py`
- `custom/justech_warranty/models/account_move.py`
- `custom/justech_warranty/models/account_move_line.py`
- `custom/justech_warranty/models/product_template.py`
- `custom/justech_warranty/models/res_company.py`
- `custom/justech_warranty/models/res_config_settings.py`
- `custom/justech_warranty/models/sale_order_line.py`
- `custom/justech_warranty/models/warranty.py`
- `custom/justech_warranty/models/warranty_claim.py`
- `custom/justech_warranty/models/warranty_claim_reason.py`
- `custom/justech_warranty/models/warranty_line_mixin.py`
- `custom/justech_warranty/models/warranty_type.py`
- `custom/justech_warranty/models/warranty_unit.py`
- `custom/justech_warranty/report/.gitkeep`
- `custom/justech_warranty/security/ir.model.access.csv`
- `custom/justech_warranty/security/warranty_security.xml`
- `custom/justech_warranty/static/description/.gitkeep`
- `custom/justech_warranty/static/description/icon.png`
- `custom/justech_warranty/static/description/index.html`
- `custom/justech_warranty/static/description/screenshots/config.png`
- `custom/justech_warranty/static/description/screenshots/dashboard.png`
- `custom/justech_warranty/static/description/screenshots/invoice_lines.png`
- `custom/justech_warranty/static/description/screenshots/launcher.png`
- `custom/justech_warranty/static/description/screenshots/warranty_form.png`
- `custom/justech_warranty/static/src/.gitkeep`
- `custom/justech_warranty/static/src/js/warranty_config_button_field.js`
- `custom/justech_warranty/static/src/scss/warranty_lines.scss`
- `custom/justech_warranty/tests/__init__.py`
- `custom/justech_warranty/tests/test_warranty.py`
- `custom/justech_warranty/views/.gitkeep`
- `custom/justech_warranty/views/account_move_views.xml`
- `custom/justech_warranty/views/menus.xml`
- `custom/justech_warranty/views/product_template_views.xml`
- `custom/justech_warranty/views/res_config_settings_views.xml`
- `custom/justech_warranty/views/sale_order_views.xml`
- `custom/justech_warranty/views/warranty_claim_views.xml`
- `custom/justech_warranty/views/warranty_config_views.xml`
- `custom/justech_warranty/views/warranty_dashboard_views.xml`
- `custom/justech_warranty/views/warranty_unit_views.xml`
- `custom/justech_warranty/views/warranty_views.xml`
- `custom/justech_warranty/wizard/__init__.py`
- `custom/justech_warranty/wizard/warranty_line_config_wizard.py`
- `custom/justech_warranty/wizard/warranty_line_config_wizard_views.xml`
- `evidence/rc-fee-ux-fix/REPORT.md`
- `evidence/rc-final-production-go-live/00_EXECUTIVE_SUMMARY.md`
- `evidence/rc-final-production-go-live/GATE_0B_WORKTREE_INVENTORY.md`
- `evidence/rc-final-production-go-live/GATE_0B_RELEASE_MANIFEST.md`

## Archivos excluidos (categoría B, no exhaustive)

- `custom/hellenia_*` (WIP paralelo / fuera del release Justech)
- `custom/justech_report_design/**` (no instalado en DEV path)
- `custom/justech_l10n_do_reports_hellenia/**`
- `custom/justech_multicurrency/**` (scss no revalidado)
- `scripts/`, `docs/`, `frontend/`, `data/coa-2/`, `.cursor/`
- Evidencias masivas fuera de `rc-final-production-go-live` y `rc-fee-ux-fix/REPORT.md`
- Backups, dumps, logs, `.env`, certificados, UAT credentials

## Pruebas Gate 0B (DEV)

- compileall Python: PASS
- XML parse: PASS (0 bad)
- Secret scan candidatos: PASS (solo atributo Odoo password=True)
- `-u` módulos release en justech_dev: PASS (odoo_exit=0, sin ERROR/CRITICAL)
- Versions DB alineadas al manifiesto: PASS
- HTTP login `https://erp.justech.do/web/login`: 200
- Assets CSS: 200
- Integridad: moves=2406, payments=699, GL_NET=0.00 (rollback shell)
- Servicio odoo-dev: active

## Riesgos conocidos

- Working tree contenía ~440 paths; solo el subset A entra al commit.
- WIP excluido se aparca en stash `gate0b-excluded-wip` para dejar status limpio (recuperable).
- Fees/garantías conteo 0 en smoke lectura (posible entorno sin registros maestros residuales); código y módulo instalados.
- e-CF laboratorio: no re-ejecución E2E DGII en este Gate (upgrade estructural OK).

## Rollback por Git

```bash
git checkout feature/fiscal-standard-consolidation
git reset --hard 2d4517494eb78c75c1e43e410e3b164acc0afa7a
# o revert del release hash en la rama, sin tocar Producción
```

Anterior HEAD: `2d4517494eb78c75c1e43e410e3b164acc0afa7a`
