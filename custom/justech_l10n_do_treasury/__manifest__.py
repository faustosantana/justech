{
    "name": "Justech Tesorería Dominicana",
    "version": "19.0.1.3.2",
    "category": "Accounting/Localizations",
    "summary": "Pagos abiertos, anticipos y experiencia de tesorería (aditivo, no destructivo)",
    "description": """
Tesorería Dominicana (Justech)
==============================
Módulo ADITIVO sobre el wizard de pagos Justech (justech.payment.partner.wizard).

- Modal XL responsive del wizard de pagos.
- Tipo de operación simplificado: Aplicar a factura / Registrar pago abierto.
- Menú Pagos abiertos (clientes y proveedores).
- Alerta en facturas con pagos abiertos del contacto.
- Wizard de aplicación posterior (solo conciliación, sin alterar contabilidad base).

No toca NCF, DGII, COA, retenciones ni el motor fiscal. Compatible con Framework Justech.
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "account",
        "account_accountant",
        "accountant",
        "justech_l10n_do_payments_withholding",
        "justech_l10n_do_reports",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/hide_duplicate_payment_menus.xml",
        "views/payment_partner_wizard_views.xml",
        "views/account_payment_open_views.xml",
        "views/account_move_open_payment_alert_views.xml",
        "views/treasury_apply_wizard_views.xml",
        "views/menu_accounting_navigation.xml",
        "data/menu_accounting_order.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_backend": [
            "justech_l10n_do_treasury/static/src/scss/treasury.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
