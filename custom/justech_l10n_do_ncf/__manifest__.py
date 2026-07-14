{
    "name": "Justech Dominican NCF",
    "version": "19.0.2.12.1",
    "category": "Accounting/Localizations",
    "summary": "NCF ranges, assignment and validation (Dominican Republic)",
    "description": """
NCF management for Dominican Republic — Justech Enterprise layer.

- NCF ranges and consumption audit
- Automatic NCF on customer invoices
- Fiscal Administration Center
- Fiscal diagnostic (read-only)
- Controlled migration legacy → Justech
- Post-sync NCF reconcile
- Duplicate detection v2.0
    """,
    "author": "Justech",
    "website": "https://justech.do",
    "depends": [
        "justech_l10n_do_base",
        "account_debit_note",
        "sale",
        "purchase",
        "sale_purchase",
        "bi_convert_purchase_from_sales",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/justech_l10n_do_ncf_rules.xml",
        "views/fiscal_admin_views.xml",
        "views/fiscal_diagnostic_views.xml",
        "views/ncf_range_views.xml",
        "views/ncf_consumption_views.xml",
        "views/ncf_migration_views.xml",
        "views/purchase_emission_config_views.xml",
        "views/purchase_received_type_views.xml",
        "views/fiscal_range_center_views.xml",
        "views/purchase_order_ux_views.xml",
        "views/account_move_views.xml",
        "views/ncf_void_wizard_views.xml",
        "views/sale_order_views.xml",
        "views/menu.xml",
        "report/report_invoice.xml",
        "report/report_invoice_l10n_do_gate.xml",
        "report/report_invoice_currency_and_ncf_validity.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
    "justech_register": {
        "module_code": "justech_l10n_do_ncf",
        "module_name": "Justech Dominican NCF",
        "version": "19.0.2.12.1",
        "category": "fiscal",
        "country": "DO",
        "localization": "l10n_do",
        "description": "NCF ranges, assignment, admin center, migration and diagnostics",
        "dependencies": ["justech_l10n_do_base"],
        "always_enabled": True,
        "required_module": True,
        "features": [
            {"code": "l10n_do_ncf", "name": "DO NCF Management"},
            {"code": "l10n_do_ncf_admin", "name": "DO Fiscal Admin Center"},
        ],
    },
    "justech_admin_center": {
        "product_code": "fiscal",
        "functional_name": "Motor NCF",
        "short_description": "Rangos, asignación y diagnóstico NCF",
        "long_description": "Qué es: motor de comprobantes fiscales NCF. Para qué sirve: asignar, controlar rangos y diagnosticar. Procesos: facturas de cliente/proveedor. Datos: secuencias NCF, tipos y consumo. Crítico: sí. Ámbito: por empresa. Al activar: permite emitir con motor tradicional o electrónico según empresa. Al desactivar: bloquea nuevas asignaciones; conserva NCF emitidos. Depende de: base fiscal.",
        "what_it_does": "Gestiona rangos y asignación de NCF por empresa.",
        "processes_affected": "Emisión de facturas, notas de crédito y compras con NCF.",
        "users_who_use_it": "Facturación, compras, contabilidad, responsable fiscal.",
        "risk_activate": "Habilita asignación de NCF en la empresa.",
        "risk_deactivate": "Impide nuevas asignaciones; no altera NCF históricos.",
        "category": "fiscal",
        "icon": "fa-file-text-o",
        "sequence": 20,
        "activation_scope": "company",
        "fiscal_engine_capable": True,
        "feature_flag_codes": ["ncf_motor"],
        "health_method": "justech.do.ncf.diagnostic.service.run_full_scan",
        "supports_activate": True,
        "supports_deactivate": True,
        "critical": True,
    },
}
