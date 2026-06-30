{
    "name": "Hellenia Account",
    "version": "19.0.1.0.2",
    "category": "Accounting/Accounting",
    "summary": "Bancos, métodos de pago y cobros/pagos Hellenia",
    "description": """
Extensiones contables Hellenia (upgrade-safe):

- Diarios bancarios DOP/USD vinculados a cuentas López de Haro
- Métodos de pago en español (Transferencia, Efectivo, Tarjeta, Cheque)
- Wizard de pago con NCF y facturas pendientes visibles
- Referencia retenciones RD (l10n_do)
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "hellenia_base",
        "account",
        "justech_l10n_do_ncf",
        "l10n_do_check_printing",
    ],
    "post_init_hook": "post_init_hook",
    "data": [
        "security/ir.model.access.csv",
        "data/payment_setup.xml",
        "views/account_payment_register_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
