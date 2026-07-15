{
    "name": "Servicios Administrados",
    "version": "19.0.2.0.1",
    "category": "Services",
    "summary": "Igualas y Servicios Administrados Justech — levantamiento, CRM, ventas, fee y Helpdesk",
    "description": """
Fase 2 — Centro operativo de Servicios Administrados / Igualas.

* Servicio Administrado (maestro) con fee, alcance y SLA básico.
* Levantamientos (Fase 1) vinculados al servicio.
* Flujo: Contacto → Levantamiento → Oportunidad → Cotización → Servicio → Fee → Tickets.
* Reutiliza CRM, Sales, Subscriptions y Helpdesk estándar (sin facturación paralela).
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
        "sale_management",
        "sale_subscription",
        "helpdesk",
        "account",
    ],
    "data": [
        "security/managed_services_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/mail_template.xml",
        "data/utm_source.xml",
        "views/managed_service_views.xml",
        "views/assessment_views.xml",
        "views/res_partner_views.xml",
        "views/crm_lead_views.xml",
        "views/sale_order_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/menu.xml",
        "report/assessment_report.xml",
        "data/report_action.xml",
        "views/website_assessment_templates.xml",
        "data/demo_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "justech_managed_services/static/src/js/assessment_clipboard.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "post_init_hook": "post_init_hook",
    "justech_register": {
        "module_code": "justech_managed_services",
        "module_name": "Servicios Administrados",
        "version": "19.0.2.0.1",
        "category": "services",
        "country": "DO",
        "localization": "",
        "description": "Igualas y Servicios Administrados — fase 2 operativa",
        "dependencies": ["crm", "sale_management", "sale_subscription", "helpdesk", "website"],
        "always_enabled": False,
        "features": [
            {
                "code": "managed_service",
                "name": "Servicio Administrado / Iguala",
            },
            {
                "code": "managed_service_assessment",
                "name": "Levantamiento Servicios Administrados",
            },
        ],
    },
}
