# -*- coding: utf-8 -*-
"""Catálogo UX de permisos operativos.

Cada ítem es una representación amigable de uno o más res.groups existentes.
No define seguridad propia: la fuente de verdad sigue siendo res.groups.
"""

OPERATIONAL_CATEGORIES = (
    {"key": "accounting", "label": "CONTABILIDAD", "sequence": 10},
    {"key": "payments", "label": "PAGOS", "sequence": 20},
    {"key": "invoicing", "label": "FACTURACIÓN", "sequence": 30},
    {"key": "purchase", "label": "COMPRAS", "sequence": 40},
    {"key": "fiscal", "label": "FISCAL", "sequence": 50},
    {"key": "withholding", "label": "RETENCIONES", "sequence": 60},
    {"key": "warranty", "label": "GARANTÍAS", "sequence": 70},
)

# xmlids: grupos que el usuario debe tener (has_group) para marcar el permiso.
# enable_xmlids: grupos a agregar al activar (por defecto = xmlids).
OPERATIONAL_PERMISSIONS = (
    # ---------------- CONTABILIDAD ----------------
    {
        "code": "acc_view",
        "category": "accounting",
        "label": "Ver contabilidad",
        "tooltip": (
            "Permite consultar asientos, diarios y reportes contables en solo lectura.\n\n"
            "No permite:\n"
            "• crear o publicar asientos\n"
            "• cancelar asientos\n"
            "• administrar configuración contable"
        ),
        "xmlids": ("account.group_account_readonly",),
    },
    {
        "code": "acc_create",
        "category": "accounting",
        "label": "Crear asientos",
        "tooltip": (
            "Permite crear asientos y trabajar con la contabilidad operativa "
            "(grupo Contabilidad / características completas).\n\n"
            "No permite:\n"
            "• administrar configuración contable avanzada\n"
            "• eliminar con privilegios de administrador"
        ),
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "acc_post",
        "category": "accounting",
        "label": "Publicar asientos",
        "tooltip": (
            "Permite publicar asientos contables dentro de las reglas estándar de Odoo.\n\n"
            "Comparte el mismo grupo técnico que «Crear asientos».\n\n"
            "No permite:\n"
            "• saltarse bloqueos de diarios o inalterabilidad"
        ),
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "acc_cancel",
        "category": "accounting",
        "label": "Cancelar asientos",
        "tooltip": (
            "Permite cancelar asientos cuando el diario y el estado del documento lo permiten.\n\n"
            "Comparte el grupo técnico de contabilidad operativa.\n\n"
            "No permite:\n"
            "• anular NCF (eso es permiso fiscal)\n"
            "• romper conciliaciones fuera del flujo estándar"
        ),
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "acc_delete_draft",
        "category": "accounting",
        "label": "Eliminar borradores",
        "tooltip": (
            "Permite eliminar borradores contables con privilegios de Administrador contable.\n\n"
            "No permite:\n"
            "• eliminar asientos publicados\n"
            "• alterar histórico publicado"
        ),
        "xmlids": ("account.group_account_manager",),
    },
    # ---------------- PAGOS ----------------
    {
        "code": "pay_view",
        "category": "payments",
        "label": "Ver pagos",
        "tooltip": (
            "Permite ver pagos y documentos de facturación relacionados.\n\n"
            "No permite:\n"
            "• registrar o aplicar pagos\n"
            "• cancelar o eliminar pagos"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "pay_register",
        "category": "payments",
        "label": "Registrar pagos",
        "tooltip": (
            "Permite registrar pagos desde el flujo de facturación/pagos de Odoo.\n\n"
            "No permite:\n"
            "• eliminar pagos\n"
            "• administrar diarios bancarios"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "pay_apply",
        "category": "payments",
        "label": "Aplicar pagos a facturas",
        "tooltip": (
            "Permite registrar y aplicar pagos a facturas abiertas.\n\n"
            "No permite:\n"
            "• eliminar pagos\n"
            "• cancelar pagos fuera del flujo estándar\n"
            "• modificar diarios\n"
            "• modificar asientos publicados"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "pay_reconcile",
        "category": "payments",
        "label": "Conciliar pagos",
        "tooltip": (
            "Permite conciliar movimientos bancarios/contables con la contabilidad operativa.\n\n"
            "No permite:\n"
            "• administrar bancos sin el permiso específico\n"
            "• borrar histórico conciliado fuera de estándar"
        ),
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "pay_unreconcile",
        "category": "payments",
        "label": "Desconciliar",
        "tooltip": (
            "Permite desconciliar cuando Odoo lo permite en el documento.\n\n"
            "Comparte el grupo de contabilidad operativa.\n\n"
            "No permite:\n"
            "• forzar desconciliación sobre asientos bloqueados"
        ),
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "pay_cancel",
        "category": "payments",
        "label": "Cancelar pagos",
        "tooltip": (
            "Permite cancelar pagos según las reglas estándar del documento.\n\n"
            "No permite:\n"
            "• eliminar pagos definitivos como Administrador\n"
            "• alterar NCF"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "pay_delete",
        "category": "payments",
        "label": "Eliminar pagos",
        "tooltip": (
            "Permite eliminar pagos en estados que Odoo autorice al Administrador contable.\n\n"
            "No permite:\n"
            "• borrar pagos conciliados bloqueados\n"
            "• alterar asientos históricos fuera de estándar"
        ),
        "xmlids": ("account.group_account_manager",),
    },
    {
        "code": "pay_bank_admin",
        "category": "payments",
        "label": "Administrar diarios bancarios",
        "tooltip": (
            "Permite validar/administrar cuentas bancarias (grupo Validar cuenta bancaria).\n\n"
            "No permite por sí solo:\n"
            "• publicar facturas\n"
            "• anular NCF"
        ),
        "xmlids": ("account.group_validate_bank_account",),
    },
    # ---------------- FACTURACIÓN ----------------
    {
        "code": "inv_view",
        "category": "invoicing",
        "label": "Ver facturas",
        "tooltip": (
            "Permite ver facturas de cliente/proveedor.\n\n"
            "No permite:\n"
            "• publicar\n"
            "• cancelar fiscales\n"
            "• emitir notas de crédito fiscales"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "inv_create",
        "category": "invoicing",
        "label": "Crear facturas",
        "tooltip": (
            "Permite crear facturas en borrador.\n\n"
            "No permite:\n"
            "• cancelar facturas fiscales sin el permiso específico\n"
            "• anular NCF"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "inv_edit_draft",
        "category": "invoicing",
        "label": "Editar borradores",
        "tooltip": (
            "Permite editar facturas en borrador.\n\n"
            "No permite:\n"
            "• modificar facturas publicadas"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "inv_post",
        "category": "invoicing",
        "label": "Publicar facturas",
        "tooltip": (
            "Permite publicar facturas y consumir NCF según Motor Fiscal.\n\n"
            "No permite:\n"
            "• anular NCF\n"
            "• administrar rangos"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "inv_cancel",
        "category": "invoicing",
        "label": "Cancelar facturas",
        "tooltip": (
            "Permite cancelar facturas fiscales (grupo l10n_do dedicated).\n\n"
            "No permite:\n"
            "• anular NCF (acción fiscal aparte)\n"
            "• borrar histórico"
        ),
        "xmlids": ("l10n_do_accounting.group_l10n_do_fiscal_invoice_cancel",),
    },
    {
        "code": "inv_credit_note",
        "category": "invoicing",
        "label": "Nota de crédito",
        "tooltip": (
            "Permite crear notas de crédito fiscales.\n\n"
            "No permite:\n"
            "• anular NCF como sustituto de NC\n"
            "• administrar rangos"
        ),
        "xmlids": ("l10n_do_accounting.group_l10n_do_fiscal_credit_note",),
    },
    # ---------------- COMPRAS ----------------
    {
        "code": "po_create",
        "category": "purchase",
        "label": "Crear solicitudes",
        "tooltip": (
            "Permite crear solicitudes/órdenes de compra (Usuario de Compras).\n\n"
            "No permite:\n"
            "• administrar compras como Administrador"
        ),
        "xmlids": ("purchase.group_purchase_user",),
    },
    {
        "code": "po_approve",
        "category": "purchase",
        "label": "Aprobar compras",
        "tooltip": (
            "Permite aprobar y administrar el flujo de compras (Administrador de Compras).\n\n"
            "No permite:\n"
            "• publicar facturas sin permiso de facturación"
        ),
        "xmlids": ("purchase.group_purchase_manager",),
    },
    {
        "code": "po_confirm",
        "category": "purchase",
        "label": "Confirmar órdenes",
        "tooltip": (
            "Permite confirmar órdenes de compra.\n\n"
            "Comparte el grupo Usuario de Compras."
        ),
        "xmlids": ("purchase.group_purchase_user",),
    },
    {
        "code": "po_bill",
        "category": "purchase",
        "label": "Facturar compras",
        "tooltip": (
            "Permite generar/procesar facturas de proveedor (Facturación).\n\n"
            "No permite:\n"
            "• administrar rangos NCF de compras emitidas"
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "po_received",
        "category": "purchase",
        "label": "Administrar documentos recibidos",
        "tooltip": (
            "Permite operar compras con documentos recibidos del proveedor (Usuario Fiscal).\n\n"
            "No permite:\n"
            "• anular NCF\n"
            "• administrar rangos"
        ),
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "po_issued",
        "category": "purchase",
        "label": "Administrar documentos emitidos",
        "tooltip": (
            "Permite emitir comprobantes de compra Justech (Responsable Fiscal).\n\n"
            "No permite:\n"
            "• administrar padrón/rangos como Administrador Fiscal"
        ),
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_manager",),
    },
    # ---------------- FISCAL ----------------
    {
        "code": "fis_rnc",
        "category": "fiscal",
        "label": "Validar RNC",
        "tooltip": (
            "Permite validar/consultar RNC en el flujo fiscal (Usuario Fiscal).\n\n"
            "No permite:\n"
            "• anular NCF\n"
            "• administrar rangos"
        ),
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fis_docs",
        "category": "fiscal",
        "label": "Seleccionar comprobantes",
        "tooltip": (
            "Permite seleccionar tipos de comprobante en documentos (Usuario Fiscal)."
        ),
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fis_void_ncf",
        "category": "fiscal",
        "label": "Anular NCF",
        "tooltip": (
            "Permite anular comprobantes fiscales (Responsable Fiscal) vía wizard 608.\n\n"
            "No permite:\n"
            "• necesariamente cancelar asientos\n"
            "• emitir nota de crédito automáticamente\n"
            "• devolver pagos"
        ),
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_manager",),
    },
    {
        "code": "fis_606",
        "category": "fiscal",
        "label": "Generar 606",
        "tooltip": "Permite generar/consultar el formato 606 (Usuario Fiscal).",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fis_607",
        "category": "fiscal",
        "label": "Generar 607",
        "tooltip": "Permite generar/consultar el formato 607 (Usuario Fiscal).",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fis_608",
        "category": "fiscal",
        "label": "Generar 608",
        "tooltip": "Permite generar/consultar el formato 608 (Usuario Fiscal).",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fis_ranges",
        "category": "fiscal",
        "label": "Administrar rangos",
        "tooltip": (
            "Permite administrar rangos NCF y consola fiscal (Administrador Fiscal).\n\n"
            "No otorga permisos contables generales por sí solo."
        ),
        "xmlids": ("justech_fiscal_admin.group_justech_fiscal_admin_manager",),
    },
    {
        "code": "fis_ecf",
        "category": "fiscal",
        "label": "Administrar e-CF",
        "tooltip": (
            "Permite operar/administrar e-CF (Administrador e-CF).\n\n"
            "No permite:\n"
            "• alterar NCF tradicionales fuera de e-CF"
        ),
        "xmlids": ("justech_ecf_core.group_ecf_admin",),
    },
    # ---------------- RETENCIONES ----------------
    {
        "code": "wh_register",
        "category": "withholding",
        "label": "Registrar",
        "tooltip": (
            "Permite registrar retenciones en el flujo de pagos/facturación."
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "wh_apply",
        "category": "withholding",
        "label": "Aplicar",
        "tooltip": (
            "Permite aplicar retenciones en pagos (Facturación)."
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "wh_approve",
        "category": "withholding",
        "label": "Aprobar",
        "tooltip": (
            "Permite aprobar/gestionar retenciones con privilegio Administrador contable."
        ),
        "xmlids": ("account.group_account_manager",),
    },
    {
        "code": "wh_admin",
        "category": "withholding",
        "label": "Administrar",
        "tooltip": (
            "Permite administrar el catálogo de retenciones Justech."
        ),
        "xmlids": (
            "justech_l10n_do_payments_withholding.group_justech_withholding_catalog_admin",
        ),
    },
    # ---------------- GARANTÍAS ----------------
    {
        "code": "war_create",
        "category": "warranty",
        "label": "Crear",
        "tooltip": "Permite crear garantías (Usuario de Garantías).",
        "xmlids": ("justech_warranty.group_warranty_user",),
    },
    {
        "code": "war_edit",
        "category": "warranty",
        "label": "Editar",
        "tooltip": "Permite editar garantías (Usuario de Garantías).",
        "xmlids": ("justech_warranty.group_warranty_user",),
    },
    {
        "code": "war_approve",
        "category": "warranty",
        "label": "Aprobar",
        "tooltip": "Permite aprobar/gestionar garantías (Responsable de Garantías).",
        "xmlids": ("justech_warranty.group_warranty_manager",),
    },
    {
        "code": "war_admin",
        "category": "warranty",
        "label": "Administrar",
        "tooltip": "Permite administrar configuración de garantías (Responsable de Garantías).",
        "xmlids": ("justech_warranty.group_warranty_manager",),
    },
)
