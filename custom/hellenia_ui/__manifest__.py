{
    "name": "Hellenia UI",
    "version": "19.0.1.0.4",
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
        "contacts",
        "stock_barcode",
    ],
    "data": [
        "views/menu_customization.xml",
        "data/menu_labels.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
