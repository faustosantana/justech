{
    "name": "Justech Pagos y Retenciones Dominicanas",
    "version": "19.0.1.3.1",
    "category": "Accounting/Localizations",
    "summary": "Pagos con retenciones fiscales dominicanas (ITBIS/ISR), 623 y trazabilidad",
    "description": """
Pagos y Retenciones Dominicanas (Justech)
==========================================

Motor estándar Justech para pagos con retención fiscal:

- Wizard unificado de cobro/pago con retenciones integradas desde un solo lugar.
- Catálogo configurable vinculado a impuestos l10n_do existentes.
- Asiento de pago + líneas de retención + conciliación automática.
- Trazabilidad factura ↔ pago ↔ retención.
- Compatible con reportes DGII 606/607/623.
    """,
    "author": "Justech",
    "website": "https://justech.do",
    "depends": [
        "account",
        "justech_l10n_do_base",
        "justech_l10n_do_ncf",
        "justech_l10n_do_reports",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/justech_withholding_catalog_views.xml",
        "views/payment_partner_wizard_views.xml",
        "views/account_payment_register_views.xml",
        "views/account_payment_withholding_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_l10n_do_payments_withholding",
        "module_name": "Pagos y Retenciones Dominicanas",
        "version": "19.0.1.3.0",
        "category": "accounting",
        "country": "DO",
        "localization": "l10n_do",
        "description": (
            "Gestión de pagos con retenciones fiscales dominicanas, ITBIS retenido, "
            "ISR retenido, conciliación y trazabilidad fiscal."
        ),
        "dependencies": ["justech_l10n_do_ncf", "justech_l10n_do_reports"],
        "always_enabled": True,
        "required_module": False,
        "features": [
            {
                "code": "payments_withholding_rd",
                "name": "Pagos y Retenciones Dominicanas",
            }
        ],
    },
}
