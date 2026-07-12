{
    "name": "Justech e-CF Queue",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Colas, reintentos, contingencia e idempotencia e-CF",
    "author": "Justech",
    "website": "https://justech.do",
    "license": "LGPL-3",
    "depends": ["justech_ecf_core", "justech_ecf_dgii"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/ecf_queue_views.xml",
    ],
    "installable": True,
}
