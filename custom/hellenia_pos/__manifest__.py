{
    "name": "Hellenia POS",
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "Point of Sale extensions for Hellenia",
    "description": """
Point of Sale extensions for Hellenia

Skeleton module — no business logic yet.
See README.md for development guidelines.
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": ["hellenia_base", "point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "hellenia_pos",
        "module_name": "Hellenia POS",
        "version": "19.0.1.0.0",
        "category": "pos",
        "country": "DO",
        "description": "Point of Sale extensions for Hellenia",
        "dependencies": ["hellenia_base"],
        "always_enabled": True,
        "features": [{"code": "hellenia_pos", "name": "Hellenia POS"}],
    },
}
