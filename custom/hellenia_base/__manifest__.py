{
    "name": "Hellenia Base",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Base configuration for Hellenia customizations",
    "description": """
Base configuration for Hellenia customizations

Skeleton module — no business logic yet.
See README.md for development guidelines.
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "hellenia_base",
        "module_name": "Hellenia Base",
        "version": "19.0.1.0.0",
        "category": "platform",
        "country": "DO",
        "localization": "",
        "description": "Base configuration for Hellenia customizations",
        "dependencies": [],
        "always_enabled": True,
        "required_module": True,
        "features": [
            {"code": "hellenia_base", "name": "Hellenia Base"},
        ],
    },
}
