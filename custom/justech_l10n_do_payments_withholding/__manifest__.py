{
    "name": "Justech Pagos y Retenciones Dominicanas",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Pagos con retenciones fiscales dominicanas (ITBIS/ISR), 623 y trazabilidad",
    "description": """
Pagos y Retenciones Dominicanas (Justech)
==========================================

Módulo comercial oficial Justech que empaqueta y expone en el catálogo de
licencias la funcionalidad de pagos con retenciones fiscales dominicanas:

- Pagos con retención (ITBIS retenido, ISR retenido).
- Retención a proveedores y a clientes (gubernamental 5% / 623).
- Comprobantes de retención y trazabilidad fiscal.
- Reporte DGII 623.

FASE ACTUAL (Etapa A — empaquetado no destructivo):
El motor de retenciones ya está entregado y activo en `hellenia_account`
(modelos `hellenia.withholding.catalog`, `hellenia.payment.withholding.line`,
`hellenia.payment.application.line` y extensiones de `account.payment` /
`account.move`). Este módulo NO mueve esa lógica todavía: solo la registra
como personalización oficial Justech `payments_withholding_rd` en el catálogo
comercial (Crear Licencia, Licencias y Personalizaciones, Módulos del Cliente)
con interruptores ON/OFF comerciales listos para cableado futuro.

La reubicación física de los modelos hacia este módulo se hará en una migración
controlada posterior (ver evidence/retenciones-1/RETENCIONES_MIGRATION_PLAN.md).
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "account",
        "justech_l10n_do_base",
        "justech_l10n_do_ncf",
        "justech_l10n_do_reports",
        "justech_modules",
    ],
    "data": [
        "data/justech_commercial_catalog.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_l10n_do_payments_withholding",
        "module_name": "Pagos y Retenciones Dominicanas",
        "version": "19.0.1.0.0",
        "category": "accounting",
        "country": "DO",
        "localization": "l10n_do",
        "description": (
            "Gestión de pagos con retenciones fiscales dominicanas, ITBIS retenido, "
            "ISR retenido, conciliación y trazabilidad fiscal."
        ),
        "dependencies": ["justech_l10n_do_ncf", "justech_l10n_do_reports"],
        "always_enabled": True,
        "required_module": False,
        "features": [
            {
                "code": "payments_withholding_rd",
                "name": "Pagos y Retenciones Dominicanas",
            }
        ],
    },
}
