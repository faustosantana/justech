{
    "name": "Justech Report Templates Test",
    "version": "19.0.1.0.0",
    "category": "Reporting",
    "summary": "Ambiente TEST para inventariar reportes QWeb estándar vs personalizados",
    "description": """
Módulo temporal de diagnóstico — solo TEST.

- No modifica reportes existentes
- No hereda vistas QWeb
- Permite ejecutar scripts de inventario de templates sale/account/purchase/stock
- Base para comparar estructura estándar Odoo vs personalizaciones Hellenia/Justech
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "sale",
        "account",
        "purchase",
        "stock",
    ],
    "data": [
        "data/redesign_structure_reference.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
