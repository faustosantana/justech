{
    "name": "Hellenia Inventory",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Inventory extensions for Hellenia",
    "description": """
Inventory extensions for Hellenia

Skeleton module — no business logic yet.
See README.md for development guidelines.
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": ["hellenia_base", "stock"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "hellenia_inventory",
        "module_name": "Hellenia Inventory",
        "version": "19.0.1.0.0",
        "category": "inventory",
        "country": "DO",
        "description": "Inventory extensions for Hellenia",
        "dependencies": ["hellenia_base"],
        "always_enabled": True,
        "features": [{"code": "hellenia_inventory", "name": "Hellenia Inventory"}],
    },
}
