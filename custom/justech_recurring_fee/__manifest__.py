# -*- coding: utf-8 -*-
{
    "name": "Justech Fees Recurrentes",
    "version": "19.0.1.0.1",
    "category": "Sales",
    "summary": "Fee recurrente como registro maestro — genera cotizaciones/facturas por ciclo",
    "description": """
Fee recurrente Justech
======================

Registro maestro operativo (no obligar cotización previa):

Fee → cron → cotización/factura → revisión → fiscales Justech → próximo ciclo.

Reutiliza `sale.subscription.plan` cuando está disponible (periodicidad),
sin forzar el flujo Cotización → Suscripción de Odoo.
""",
    "author": "Justech",
    "website": "https://justech.do",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "account",
        "mail",
        "sale_subscription",
    ],
    "data": [
        "security/recurring_fee_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/ir_cron.xml",
        "views/recurring_fee_views.xml",
        "wizard/fee_reactivate_wizard_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
