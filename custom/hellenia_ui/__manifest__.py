{
    "name": "Hellenia UI",
    "version": "19.0.1.0.12",
    "category": "Hidden",
    "summary": "Menú principal y etiquetas UI para Hellenia (upgrade-safe)",
    "description": """
Personalización de menús y aplicaciones para Hellenia:

- Activa la aplicación Ventas (requiere sale_management)
- Renombra Facturación → Contabilidad
- Renombra Settings → Configuración
- Restringe Apps a administradores técnicos (base.group_system)
- Oculta Código de barras (fuera de alcance)
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "base",
        "sale_management",
        "purchase",
        "stock",
        "account",
        "account_accountant",
        "contacts",
        "stock_barcode",
        "justech_l10n_do_treasury",
        "hellenia_account",
        "justech_l10n_do_reports",
    ],
    "data": [
        "views/menu_customization.xml",
        "data/menu_accounting_navigation.xml",
        "data/menu_purchase_navigation.xml",
        "data/menu_labels.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "hellenia_ui",
        "module_name": "Hellenia UI",
        "version": "19.0.1.0.11",
        "category": "ux",
        "country": "DO",
        "description": "Main menu and UI labels for Hellenia",
        "dependencies": ["hellenia_base"],
        "always_enabled": True,
        "features": [{"code": "hellenia_ui", "name": "Hellenia UI"}],
    },
}
