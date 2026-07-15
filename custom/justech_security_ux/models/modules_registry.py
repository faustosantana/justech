# -*- coding: utf-8 -*-
"""Registry UX → grupos reales de Odoo (sin inventar seguridad paralela).

Cada sección:
- levels: escalera mutua (Selection) → xmlids reales
- caps: capacidades booleanas → xmlids reales y segregables
- module_xmlids: módulos Odoo que deben estar instalados para mostrar la sección
"""

# Riesgo: lectura | operativo | aprobacion | administracion | critico

JX_MODULES = (
    {
        "key": "sales",
        "label": "Ventas",
        "modules": ("sale",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("operar cotizaciones ni pedidos de venta",),
                "risk": "lectura",
            },
            {
                "code": "own",
                "label": "Usuario: solo sus documentos",
                "xmlids": ("sales_team.group_sale_salesman",),
                "can": (
                    "crear y gestionar sus propias cotizaciones/pedidos",
                    "confirmar sus pedidos (según flujo estándar)",
                ),
                "cannot": (
                    "ver documentos de otros vendedores",
                    "administrar equipos ni configuración de Ventas",
                ),
                "risk": "operativo",
            },
            {
                "code": "all",
                "label": "Usuario: todos los documentos",
                "xmlids": ("sales_team.group_sale_salesman_all_leads",),
                "can": (
                    "ver y operar cotizaciones/pedidos de todos los vendedores",
                ),
                "cannot": ("administrar configuración de Ventas",),
                "risk": "operativo",
            },
            {
                "code": "manager",
                "label": "Administrador",
                "xmlids": ("sales_team.group_sale_manager",),
                "can": (
                    "administrar Ventas (equipos, reportes, configuración autorizada)",
                    "operar todos los documentos comerciales",
                ),
                "cannot": ("administrar usuarios del sistema",),
                "risk": "administracion",
            },
        ),
        "caps": (
            {
                "code": "so_discount",
                "label": "Aplicar descuentos en líneas",
                "xmlids": ("sale.group_discount_per_so_line",),
                "can": ("aplicar descuento porcentual por línea de venta",),
                "cannot": ("aprobar políticas de descuento ajenas al grupo",),
                "risk": "aprobacion",
                "help": "Grupo estándar sale.group_discount_per_so_line.",
            },
            {
                "code": "so_credit_note",
                "label": "Emitir notas de crédito fiscales",
                "xmlids": ("l10n_do_accounting.group_l10n_do_fiscal_credit_note",),
                "can": ("crear notas de crédito fiscales (l10n_do)",),
                "cannot": ("anular NCF ni administrar rangos",),
                "risk": "aprobacion",
                "modules": ("l10n_do_accounting",),
                "help": "Grupo l10n_do_accounting.group_l10n_do_fiscal_credit_note.",
            },
            {
                "code": "so_cancel_fiscal",
                "label": "Cancelar facturas fiscales",
                "xmlids": ("l10n_do_accounting.group_l10n_do_fiscal_invoice_cancel",),
                "can": ("cancelar facturas fiscales cuando el flujo l10n_do lo permite",),
                "cannot": ("garantizar anulación NCF sin grupo fiscal correspondiente",),
                "risk": "critico",
                "modules": ("l10n_do_accounting",),
                "help": "Grupo l10n_do_accounting.group_l10n_do_fiscal_invoice_cancel.",
            },
        ),
    },
    {
        "key": "purchase",
        "label": "Compras",
        "modules": ("purchase",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("operar solicitudes ni órdenes de compra",),
                "risk": "lectura",
            },
            {
                "code": "user",
                "label": "Usuario",
                "xmlids": ("purchase.group_purchase_user",),
                "can": (
                    "crear solicitudes y órdenes de compra",
                    "seguir el flujo de aprobación estándar de su nivel",
                ),
                "cannot": ("administrar configuración de Compras",),
                "risk": "operativo",
            },
            {
                "code": "manager",
                "label": "Administrador",
                "xmlids": ("purchase.group_purchase_manager",),
                "can": (
                    "aprobar y administrar compras",
                    "configurar parámetros de Compras autorizados",
                ),
                "cannot": ("administrar usuarios del sistema",),
                "risk": "administracion",
            },
        ),
        "caps": (),
        "notes": (
            "Documentos recibidos / B11-B13-B17 no tienen grupos propios de Compras; "
            "dependen de Contabilidad + roles Fiscal (sección dinámica)."
        ),
    },
    {
        "key": "inventory",
        "label": "Inventario",
        "modules": ("stock",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("operar transferencias ni ajustes",),
                "risk": "lectura",
            },
            {
                "code": "user",
                "label": "Usuario",
                "xmlids": ("stock.group_stock_user",),
                "can": (
                    "registrar entradas/salidas y transferencias",
                    "participar en conteos según flujos estándar",
                ),
                "cannot": ("administrar valoración ni configuración de almacenes",),
                "risk": "operativo",
            },
            {
                "code": "manager",
                "label": "Administrador",
                "xmlids": ("stock.group_stock_manager",),
                "can": (
                    "administrar inventario, ubicaciones y valoración autorizada",
                    "validar operaciones de inventario",
                ),
                "cannot": ("administrar usuarios del sistema",),
                "risk": "administracion",
            },
        ),
        "caps": (
            {
                "code": "stk_lots",
                "label": "Registrar seriales / lotes",
                "xmlids": ("stock.group_production_lot",),
                "can": ("usar seguimiento por lote/número de serie",),
                "cannot": ("cambiar valoración contable por sí solo",),
                "risk": "operativo",
                "help": "Grupo stock.group_production_lot.",
            },
        ),
    },
    {
        "key": "accounting",
        "label": "Contabilidad",
        "modules": ("account",),
        # Incluidos en el ladder gestionado aunque no sean opciones de UI
        "ladder_extra_xmlids": (
            "account.group_account_readonly",
            "account.group_account_basic",
        ),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("facturar, contabilizar ni administrar diarios",),
                "risk": "lectura",
            },
            {
                "code": "invoice",
                "label": "Facturación",
                "xmlids": ("account.group_account_invoice",),
                "can": (
                    "crear y publicar facturas/notas",
                    "registrar y aplicar pagos sobre documentos abiertos "
                    "(Odoo concede cobros, pagos y aplicación con el mismo grupo)",
                ),
                "cannot": (
                    "funciones completas de contabilidad (asientos avanzados)",
                    "administrar plan de cuentas / Impuestos / diarios como Administrador",
                ),
                "risk": "operativo",
                "warning": (
                    "Este nivel también concede, vía el mismo grupo Odoo: "
                    "registrar cobros, registrar pagos a proveedores y aplicar pagos a facturas. "
                    "No existe en esta instancia un grupo separado que distinga esas tres acciones."
                ),
            },
            {
                "code": "accountant",
                "label": "Contabilidad",
                "xmlids": ("account.group_account_user",),
                "can": (
                    "usar características completas de contabilidad",
                    "operar asientos y reportes contables estándar",
                ),
                "cannot": ("administrar configuración contable completa",),
                "risk": "aprobacion",
            },
            {
                "code": "manager",
                "label": "Administrador",
                "xmlids": ("account.group_account_manager",),
                "can": (
                    "administrar Contabilidad (diarios, impuestos, configuración)",
                    "gestionar catálogo de retenciones (implicación hacia Administrador de Retenciones)",
                ),
                "cannot": ("administrar usuarios del sistema por sí solo",),
                "risk": "critico",
                "warning": (
                    "Alto riesgo. Implica Facturación/Contabilidad y, en esta BD, "
                    "el catálogo de retenciones Justech."
                ),
            },
        ),
        "caps": (),
        "notes": (
            "Las capacidades fiscales DGII/NCF se administran en «Fiscal República Dominicana». "
            "Pagos/Bancos detalla lo que Facturación realmente concede."
        ),
    },
    {
        "key": "fiscal",
        "label": "Fiscal República Dominicana",
        "modules": ("justech_l10n_do_base",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso fiscal",
                "xmlids": (),
                "can": (),
                "cannot": ("operar funciones fiscales Justech",),
                "risk": "lectura",
            },
            {
                "code": "user",
                "label": "Usuario Fiscal",
                "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
                "can": (
                    "consultar información fiscal cotidiana",
                    "seleccionar tipos de comprobante en documentos",
                    "operar flujos fiscales de usuario (implica Facturación)",
                ),
                "cannot": (
                    "administrar rangos NCF",
                    "administrar configuración fiscal avanzada",
                ),
                "risk": "operativo",
                "warning": "Implica account.group_account_invoice (Facturación).",
            },
            {
                "code": "officer",
                "label": "Responsable Fiscal",
                "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_manager",),
                "can": (
                    "anular NCF según flujo Justech",
                    "gestionar operaciones fiscales avanzadas de responsable",
                    "generar/consultar reportes DGII autorizados a Responsable",
                ),
                "cannot": ("administrar configuración global de Fiscal Admin",),
                "risk": "aprobacion",
            },
            {
                "code": "admin",
                "label": "Administrador Fiscal",
                "xmlids": ("justech_fiscal_admin.group_justech_fiscal_admin_manager",),
                "can": (
                    "administrar rangos, tipos y configuración fiscal Justech",
                    "resolver incidencias fiscales",
                    "acceso de administración fiscal (alto privilegio)",
                ),
                "cannot": (
                    "administrar usuarios Odoo (base.group_system) por sí solo",
                    "obtener Inventario/Compras salvo otras asignaciones",
                ),
                "risk": "critico",
                "modules": ("justech_fiscal_admin",),
                "warning": (
                    "Crítico. Puede implicar e-CF Admin vía bridge Justech; "
                    "no concede Administración de Usuarios."
                ),
            },
        ),
        "caps": (),
    },
    {
        "key": "payments",
        "label": "Pagos y Bancos",
        "modules": ("account",),
        "levels": (),
        "caps": (
            {
                "code": "pay_invoice_access",
                "label": "Acceso a facturación y pagos (grupo Odoo)",
                "xmlids": ("account.group_account_invoice",),
                "can": (
                    "ver/registrar facturas",
                    "registrar cobros de clientes",
                    "registrar pagos a proveedores",
                    "aplicar pagos a facturas abiertas",
                ),
                "cannot": (
                    "una segregación independiente cobro vs pago vs aplicar "
                    "(no existe grupo separado en esta instancia)",
                    "administrar diarios como Administrador Contable",
                ),
                "risk": "operativo",
                "warning": (
                    "ADVERTENCIA: un solo grupo Odoo (account.group_account_invoice) "
                    "concede facturación + cobros + pagos + aplicación. "
                    "No se afirma segregación fina inexistente."
                ),
                "help": "Equivale al nivel Facturación de Contabilidad; se sincroniza con ese mismo grupo.",
                "aliases_level": ("accounting", "invoice"),
            },
            {
                "code": "pay_bank_validate",
                "label": "Validar / administrar cuentas bancarias",
                "xmlids": ("account.group_validate_bank_account",),
                "can": ("validar cuentas bancarias (privilege Banco Odoo)",),
                "cannot": ("reemplazar al Administrador Contable",),
                "risk": "administracion",
                "help": "Grupo account.group_validate_bank_account.",
            },
        ),
        "notes": (
            "Cancelar/eliminar pagos depende de ACL/estados Odoo del grupo efectivo; "
            "se valida en UAT con usuario temporal, no por afirmación de UI."
        ),
    },
    {
        "key": "withholding",
        "label": "Retenciones",
        "modules": ("justech_l10n_do_payments_withholding",),
        "levels": (
            {
                "code": "none",
                "label": "Sin administración de catálogo",
                "xmlids": (),
                "can": (),
                "cannot": ("administrar el catálogo Justech de retenciones",),
                "risk": "lectura",
            },
            {
                "code": "catalog_admin",
                "label": "Administrador de Retenciones",
                "xmlids": (
                    "justech_l10n_do_payments_withholding.group_justech_withholding_catalog_admin",
                ),
                "can": (
                    "administrar catálogo de retenciones Justech",
                ),
                "cannot": (
                    "sustituir el flujo operativo de aplicación en pagos "
                    "(ese flujo usa grupos Contabilidad/Facturación)",
                ),
                "risk": "administracion",
                "warning": (
                    "Puede estar implícito por Contabilidad / Administrador. "
                    "Quitar solo este nivel no elimina account.group_account_manager."
                ),
            },
        ),
        "caps": (),
        "notes": (
            "Registrar/aplicar retenciones en pagos: requiere Facturación/Contabilidad; "
            "no hay grupo «Usuario Retenciones» separado."
        ),
    },
    {
        "key": "ecf",
        "label": "e-CF",
        "modules": ("justech_ecf_core",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("acceder a operaciones e-CF",),
                "risk": "lectura",
            },
            {
                "code": "readonly",
                "label": "Solo lectura e-CF",
                "xmlids": ("justech_ecf_core.group_ecf_readonly",),
                "can": ("consultar documentos/eventos e-CF en lectura",),
                "cannot": ("enviar ni administrar e-CF",),
                "risk": "lectura",
            },
            {
                "code": "operator",
                "label": "Operador e-CF",
                "xmlids": ("justech_ecf_core.group_ecf_operator",),
                "can": ("operar envíos e-CF cotidianos",),
                "cannot": ("administrar configuración e-CF",),
                "risk": "operativo",
            },
            {
                "code": "responsible",
                "label": "Responsable e-CF",
                "xmlids": ("justech_ecf_core.group_ecf_responsible",),
                "can": ("supervisar operaciones e-CF",),
                "cannot": ("administración completa e-CF",),
                "risk": "aprobacion",
            },
            {
                "code": "admin",
                "label": "Administrador e-CF",
                "xmlids": ("justech_ecf_core.group_ecf_admin",),
                "can": ("administrar configuración e-CF",),
                "cannot": ("administrar usuarios Odoo por sí solo",),
                "risk": "critico",
            },
        ),
        "caps": (
            {
                "code": "ecf_auditor",
                "label": "Auditor e-CF",
                "xmlids": ("justech_ecf_core.group_ecf_auditor",),
                "can": ("auditar historial/eventos e-CF",),
                "cannot": ("administrar configuración e-CF",),
                "risk": "lectura",
            },
        ),
    },
    {
        "key": "warranty",
        "label": "Garantías",
        "modules": ("justech_warranty",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("usar el módulo de garantías",),
                "risk": "lectura",
            },
            {
                "code": "user",
                "label": "Usuario de Garantías",
                "xmlids": ("justech_warranty.group_warranty_user",),
                "can": ("ver, crear y procesar garantías según ACL del grupo",),
                "cannot": ("administrar configuración completa de garantías",),
                "risk": "operativo",
            },
            {
                "code": "manager",
                "label": "Administrador de Garantías",
                "xmlids": ("justech_warranty.group_warranty_manager",),
                "can": ("administrar garantías (incluye eliminación según ACL)",),
                "cannot": ("administrar usuarios Odoo por sí solo",),
                "risk": "administracion",
            },
        ),
        "caps": (),
    },
    {
        "key": "fees",
        "label": "Fees recurrentes",
        "modules": ("justech_recurring_fee",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("gestionar fees recurrentes",),
                "risk": "lectura",
            },
            {
                "code": "user",
                "label": "Usuario Fees",
                "xmlids": ("justech_recurring_fee.group_recurring_fee_user",),
                "can": ("operar fees recurrentes (implica Usuario Ventas propios)",),
                "cannot": ("administrar configuración de Fees",),
                "risk": "operativo",
                "warning": "Implica sales_team.group_sale_salesman.",
            },
            {
                "code": "manager",
                "label": "Responsable Fees",
                "xmlids": ("justech_recurring_fee.group_recurring_fee_manager",),
                "can": ("administrar fees recurrentes",),
                "cannot": ("administrar usuarios Odoo por sí solo",),
                "risk": "administracion",
            },
        ),
        "caps": (),
    },
    {
        "key": "crm",
        "label": "CRM",
        "modules": ("crm",),
        "levels": (
            {
                "code": "none",
                "label": "Sin flag de Leads",
                "xmlids": (),
                "can": (),
                "cannot": ("mostrar menú de Leads (flag CRM)",),
                "risk": "lectura",
            },
            {
                "code": "leads",
                "label": "Usar Leads",
                "xmlids": ("crm.group_use_lead",),
                "can": ("mostrar el menú de Leads",),
                "cannot": (
                    "sustituir la escalera de Ventas (el acceso CRM operativo "
                    "sigue dependiendo de grupos de Ventas)",
                ),
                "risk": "operativo",
                "warning": "En Odoo no existe escalera CRM User/Admin independiente de Ventas.",
            },
        ),
        "caps": (),
    },
    {
        "key": "hr",
        "label": "Recursos Humanos",
        "modules": ("hr",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("gestionar empleados",),
                "risk": "lectura",
            },
            {
                "code": "user",
                "label": "Encargado",
                "xmlids": ("hr.group_hr_user",),
                "can": ("gestionar empleados como Encargado",),
                "cannot": ("administrar configuración HR completa",),
                "risk": "operativo",
            },
            {
                "code": "manager",
                "label": "Administrador",
                "xmlids": ("hr.group_hr_manager",),
                "can": ("administrar Empleados/HR",),
                "cannot": ("administrar usuarios Odoo por sí solo",),
                "risk": "administracion",
            },
        ),
        "caps": (),
    },
    {
        "key": "admin",
        "label": "Administración Justech",
        "modules": ("justech_admin_center",),
        "levels": (
            {
                "code": "none",
                "label": "Sin acceso",
                "xmlids": (),
                "can": (),
                "cannot": ("usar consola Justech Admin Center",),
                "risk": "lectura",
            },
            {
                "code": "user",
                "label": "Usuario consola Justech",
                "xmlids": ("justech_admin_center.group_justech_admin_center_user",),
                "can": ("usar funciones de usuario del Admin Center",),
                "cannot": ("administrar el Admin Center",),
                "risk": "operativo",
            },
            {
                "code": "manager",
                "label": "Administrador Justech",
                "xmlids": ("justech_admin_center.group_justech_admin_center_manager",),
                "can": ("administrar Justech Admin Center",),
                "cannot": ("equivaler automáticamente a Administrador del Sistema Odoo",),
                "risk": "critico",
                "warning": "Puede implicar e-CF Admin vía bridge; verificar implied_ids.",
            },
        ),
        "caps": (),
    },
)
