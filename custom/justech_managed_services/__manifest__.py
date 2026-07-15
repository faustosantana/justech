{
    "name": "Servicios Administrados",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Levantamientos de Servicios Administrados — formulario público y CRM",
    "description": """
Fase 1 — Levantamientos de Servicios Administrados Justech.

* Formulario público multipágina con enlace seguro por token.
* Guardado parcial y envío final.
* PDF, plantilla de correo e integración con contactos y CRM.
    """,
    "author": "Justech",
    "website": "https://justech.do",
    "depends": [
        "base",
        "mail",
        "contacts",
        "crm",
        "website",
        "portal",
    ],
    "data": [
        "security/managed_services_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/mail_template.xml",
        "data/utm_source.xml",
        "views/assessment_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/menu.xml",
        "report/assessment_report.xml",
        "data/report_action.xml",
        "views/website_assessment_templates.xml",
        "data/demo_data.xml",
    ],
    "assets": {},
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
    "justech_register": {
        "module_code": "justech_managed_services",
        "module_name": "Servicios Administrados",
        "version": "19.0.1.0.0",
        "category": "services",
        "country": "DO",
        "localization": "",
        "description": "Levantamientos de Servicios Administrados — fase 1",
        "dependencies": ["crm", "website"],
        "always_enabled": False,
        "features": [
            {
                "code": "managed_service_assessment",
                "name": "Levantamiento Servicios Administrados",
            },
        ],
    },
}
