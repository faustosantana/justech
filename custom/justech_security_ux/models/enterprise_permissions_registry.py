# -*- coding: utf-8 -*-
"""Catálogo UX Enterprise — roles y acciones → res.groups (única fuente de verdad)."""

# Navegación por responsabilidades (OPERACIÓN)
ENTERPRISE_CATEGORIES = (
    {"key": "commercial", "label": "Comercial", "sequence": 10},
    {"key": "purchase", "label": "Compras", "sequence": 20},
    {"key": "inventory", "label": "Inventario", "sequence": 30},
    {"key": "finance", "label": "Finanzas", "sequence": 40},
    {"key": "accounting", "label": "Contabilidad", "sequence": 50},
    {"key": "fiscal", "label": "Fiscal", "sequence": 60},
    {"key": "ecf", "label": "e-CF", "sequence": 70},
    {"key": "warranty", "label": "Garantías", "sequence": 80},
    {"key": "hr", "label": "Recursos Humanos", "sequence": 90},
    {"key": "crm", "label": "CRM", "sequence": 100},
    {"key": "admin", "label": "Administración Justech", "sequence": 110},
)

# Roles exclusivos por categoría (tarjeta = un nivel). xmlids = grupo a asignar.
ENTERPRISE_ROLES = (
    # Comercial
    {
        "code": "commercial_own",
        "category": "commercial",
        "label": "Usuario de ventas (propios)",
        "level": 1,
        "bullets": (
            "Crear cotizaciones y pedidos propios",
            "Confirmar ventas de sus documentos",
            "Consultar su cartera",
        ),
        "xmlids": ("sales_team.group_sale_salesman",),
    },
    {
        "code": "commercial_all",
        "category": "commercial",
        "label": "Usuario de ventas (todos)",
        "level": 2,
        "bullets": (
            "Todo lo del usuario propios",
            "Ver y operar todos los documentos de venta",
        ),
        "xmlids": ("sales_team.group_sale_salesman_all_leads",),
    },
    {
        "code": "commercial_admin",
        "category": "commercial",
        "label": "Administrador comercial",
        "level": 3,
        "bullets": (
            "Todo lo anterior",
            "Administrar equipo y configuración comercial",
        ),
        "xmlids": ("sales_team.group_sale_manager",),
    },
    # Compras
    {
        "code": "purchase_user",
        "category": "purchase",
        "label": "Usuario de compras",
        "level": 1,
        "bullets": (
            "Crear solicitudes y órdenes",
            "Confirmar órdenes",
            "Seguimiento a proveedores",
        ),
        "xmlids": ("purchase.group_purchase_user",),
    },
    {
        "code": "purchase_admin",
        "category": "purchase",
        "label": "Administrador de compras",
        "level": 2,
        "bullets": (
            "Todo lo del usuario de compras",
            "Aprobar y administrar el flujo de compras",
        ),
        "xmlids": ("purchase.group_purchase_manager",),
    },
    # Inventario
    {
        "code": "inventory_user",
        "category": "inventory",
        "label": "Usuario de inventario",
        "level": 1,
        "bullets": (
            "Entradas y salidas",
            "Transferencias y ajustes operativos",
        ),
        "xmlids": ("stock.group_stock_user",),
    },
    {
        "code": "inventory_admin",
        "category": "inventory",
        "label": "Administrador de inventario",
        "level": 2,
        "bullets": (
            "Todo lo del usuario de inventario",
            "Configurar almacenes y flujos",
        ),
        "xmlids": ("stock.group_stock_manager",),
    },
    # Finanzas
    {
        "code": "finance_invoice",
        "category": "finance",
        "label": "Facturación y pagos",
        "level": 1,
        "bullets": (
            "Registrar cobros y pagos",
            "Aplicar pagos a facturas",
            "Emitir facturas",
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "finance_book",
        "category": "finance",
        "label": "Contable operativo",
        "level": 2,
        "bullets": (
            "Todo lo de facturación y pagos",
            "Conciliar y desconciliar",
            "Operar asientos",
        ),
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "finance_admin",
        "category": "finance",
        "label": "Administrador financiero",
        "level": 3,
        "bullets": (
            "Todo lo anterior",
            "Aprobar y eliminar con privilegio administrador",
            "Configuración financiera",
        ),
        "xmlids": ("account.group_account_manager",),
    },
    # Contabilidad (misma escalera, lectura incluida)
    {
        "code": "accounting_ro",
        "category": "accounting",
        "label": "Consulta contable",
        "level": 1,
        "bullets": (
            "Ver asientos y reportes",
            "Sin publicar ni cancelar",
        ),
        "xmlids": ("account.group_account_readonly",),
    },
    {
        "code": "accounting_ops",
        "category": "accounting",
        "label": "Contabilidad operativa",
        "level": 2,
        "bullets": (
            "Crear y publicar asientos",
            "Cancelar cuando el diario lo permita",
        ),
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "accounting_admin",
        "category": "accounting",
        "label": "Administrador contable",
        "level": 3,
        "bullets": (
            "Todo lo anterior",
            "Eliminar borradores y configurar contabilidad",
        ),
        "xmlids": ("account.group_account_manager",),
    },
    # Fiscal
    {
        "code": "fiscal_user",
        "category": "fiscal",
        "label": "Usuario Fiscal",
        "level": 1,
        "bullets": (
            "Emitir NCF en el flujo estándar",
            "Validar RNC / seleccionar comprobantes",
            "Consultar reportes DGII (606/607/608)",
        ),
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fiscal_officer",
        "category": "fiscal",
        "label": "Responsable Fiscal",
        "level": 2,
        "bullets": (
            "Todo lo del Usuario Fiscal",
            "Generar 606 / 607 / 608",
            "Anular NCF",
            "Documentos de compra emitidos",
        ),
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_manager",),
    },
    {
        "code": "fiscal_admin",
        "category": "fiscal",
        "label": "Administrador Fiscal",
        "level": 3,
        "bullets": (
            "Todo lo del Responsable Fiscal",
            "Configurar rangos",
            "Configurar tipos y DGII",
            "Administrar padrón y consola fiscal",
        ),
        "xmlids": ("justech_fiscal_admin.group_justech_fiscal_admin_manager",),
    },
    # e-CF
    {
        "code": "ecf_ro",
        "category": "ecf",
        "label": "Solo lectura e-CF",
        "level": 1,
        "bullets": ("Consultar documentos electrónicos",),
        "xmlids": ("justech_ecf_core.group_ecf_readonly",),
    },
    {
        "code": "ecf_op",
        "category": "ecf",
        "label": "Operador e-CF",
        "level": 2,
        "bullets": ("Todo lo de lectura", "Operar emisión e-CF"),
        "xmlids": ("justech_ecf_core.group_ecf_operator",),
    },
    {
        "code": "ecf_resp",
        "category": "ecf",
        "label": "Responsable e-CF",
        "level": 3,
        "bullets": ("Todo lo del operador", "Supervisar el flujo e-CF"),
        "xmlids": ("justech_ecf_core.group_ecf_responsible",),
    },
    {
        "code": "ecf_admin",
        "category": "ecf",
        "label": "Administrador e-CF",
        "level": 4,
        "bullets": ("Todo lo anterior", "Administrar configuración e-CF"),
        "xmlids": ("justech_ecf_core.group_ecf_admin",),
    },
    # Garantías
    {
        "code": "warranty_user",
        "category": "warranty",
        "label": "Usuario de Garantías",
        "level": 1,
        "bullets": (
            "Crear garantías",
            "Modificar y consultar historial",
        ),
        "xmlids": ("justech_warranty.group_warranty_user",),
    },
    {
        "code": "warranty_admin",
        "category": "warranty",
        "label": "Responsable de Garantías",
        "level": 2,
        "bullets": (
            "Todo lo del usuario",
            "Procesar / aprobar y administrar",
        ),
        "xmlids": ("justech_warranty.group_warranty_manager",),
    },
    # RRHH
    {
        "code": "hr_user",
        "category": "hr",
        "label": "Encargado de empleados",
        "level": 1,
        "bullets": ("Gestionar empleados", "Operación de RRHH"),
        "xmlids": ("hr.group_hr_user",),
    },
    {
        "code": "hr_admin",
        "category": "hr",
        "label": "Administrador de empleados",
        "level": 2,
        "bullets": ("Todo lo del encargado", "Administrar configuración de RRHH"),
        "xmlids": ("hr.group_hr_manager",),
    },
    # CRM
    {
        "code": "crm_leads",
        "category": "crm",
        "label": "CRM con leads",
        "level": 1,
        "bullets": ("Mostrar y operar menú de leads",),
        "xmlids": ("crm.group_use_lead",),
    },
    # Admin Justech
    {
        "code": "admin_user",
        "category": "admin",
        "label": "Usuario consola Justech",
        "level": 1,
        "bullets": ("Acceso de consulta a la consola Justech",),
        "xmlids": ("justech_admin_center.group_justech_admin_center_user",),
    },
    {
        "code": "admin_manager",
        "category": "admin",
        "label": "Administrador Justech",
        "level": 2,
        "bullets": (
            "Todo lo del usuario consola",
            "Activar módulos y operaciones de administración",
        ),
        "xmlids": ("justech_admin_center.group_justech_admin_center_manager",),
    },
)

# Acciones operativas por categoría
ENTERPRISE_ACTIONS = (
    # Finanzas
    {
        "code": "fin_register_in",
        "category": "finance",
        "label": "Registrar cobros",
        "tooltip": "Permite registrar cobros de clientes. No permite eliminar pagos.",
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "fin_register_out",
        "category": "finance",
        "label": "Registrar pagos",
        "tooltip": "Permite registrar pagos a proveedores. No permite eliminarlos.",
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "fin_apply",
        "category": "finance",
        "label": "Aplicar pagos",
        "tooltip": (
            "Permite aplicar pagos registrados a facturas existentes. "
            "No permite eliminarlos."
        ),
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "fin_reconcile",
        "category": "finance",
        "label": "Reconciliar",
        "tooltip": "Permite conciliar movimientos bancarios y contables.",
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "fin_unreconcile",
        "category": "finance",
        "label": "Desconciliar",
        "tooltip": "Permite desconciliar cuando el documento lo permite.",
        "xmlids": ("account.group_account_user",),
    },
    {
        "code": "fin_approve",
        "category": "finance",
        "label": "Aprobar pagos",
        "tooltip": "Permite aprobar/gestionar pagos con privilegio administrador.",
        "xmlids": ("account.group_account_manager",),
    },
    {
        "code": "fin_bank_create",
        "category": "finance",
        "label": "Crear diarios",
        "tooltip": "Permite administrar diarios/cuentas bancarias (validación bancaria).",
        "xmlids": ("account.group_validate_bank_account",),
    },
    {
        "code": "fin_bank_edit",
        "category": "finance",
        "label": "Modificar diarios",
        "tooltip": "Permite modificar configuración bancaria autorizada.",
        "xmlids": ("account.group_validate_bank_account",),
    },
    {
        "code": "fin_export",
        "category": "finance",
        "label": "Exportar",
        "tooltip": "Permite exportar información financiera según permisos de Odoo.",
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "fin_reports",
        "category": "finance",
        "label": "Ver reportes",
        "tooltip": "Permite consultar reportes de facturación y pagos.",
        "xmlids": ("account.group_account_invoice",),
    },
    # Compras
    {
        "code": "po_request",
        "category": "purchase",
        "label": "Crear solicitud",
        "tooltip": "Permite crear solicitudes de compra.",
        "xmlids": ("purchase.group_purchase_user",),
    },
    {
        "code": "po_approve_req",
        "category": "purchase",
        "label": "Aprobar solicitud",
        "tooltip": "Permite aprobar solicitudes (Administrador de compras).",
        "xmlids": ("purchase.group_purchase_manager",),
    },
    {
        "code": "po_order",
        "category": "purchase",
        "label": "Crear orden",
        "tooltip": "Permite crear órdenes de compra.",
        "xmlids": ("purchase.group_purchase_user",),
    },
    {
        "code": "po_approve_order",
        "category": "purchase",
        "label": "Aprobar orden",
        "tooltip": "Permite aprobar órdenes de compra.",
        "xmlids": ("purchase.group_purchase_manager",),
    },
    {
        "code": "po_vendor_bill",
        "category": "purchase",
        "label": "Registrar factura proveedor",
        "tooltip": "Permite registrar facturas de proveedor.",
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "po_received",
        "category": "purchase",
        "label": "Registrar documento recibido",
        "tooltip": "Permite registrar compras con NCF recibido del proveedor.",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "po_b11",
        "category": "purchase",
        "label": "Emitir B11",
        "tooltip": "Permite emitir comprobantes de compra B11 (Responsable Fiscal).",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_manager",),
    },
    {
        "code": "po_b13",
        "category": "purchase",
        "label": "Emitir B13",
        "tooltip": "Permite emitir comprobantes de compra B13 (Responsable Fiscal).",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_manager",),
    },
    {
        "code": "po_b17",
        "category": "purchase",
        "label": "Emitir B17",
        "tooltip": "Permite emitir comprobantes de compra B17 (Responsable Fiscal).",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_manager",),
    },
    {
        "code": "po_cancel",
        "category": "purchase",
        "label": "Cancelar orden",
        "tooltip": "Permite cancelar órdenes según el flujo estándar.",
        "xmlids": ("purchase.group_purchase_user",),
    },
    {
        "code": "po_delete",
        "category": "purchase",
        "label": "Eliminar orden",
        "tooltip": "Permite eliminar órdenes en estados autorizados (Administrador).",
        "xmlids": ("purchase.group_purchase_manager",),
    },
    # Ventas / Comercial
    {
        "code": "so_quote",
        "category": "commercial",
        "label": "Crear cotización",
        "tooltip": "Permite crear cotizaciones de venta.",
        "xmlids": ("sales_team.group_sale_salesman",),
    },
    {
        "code": "so_approve",
        "category": "commercial",
        "label": "Aprobar cotización",
        "tooltip": "Permite aprobar cotizaciones (Administrador comercial).",
        "xmlids": ("sales_team.group_sale_manager",),
    },
    {
        "code": "so_confirm",
        "category": "commercial",
        "label": "Confirmar venta",
        "tooltip": "Permite confirmar pedidos de venta.",
        "xmlids": ("sales_team.group_sale_salesman",),
    },
    {
        "code": "so_invoice",
        "category": "commercial",
        "label": "Emitir factura",
        "tooltip": "Permite emitir facturas desde ventas/facturación.",
        "xmlids": ("account.group_account_invoice",),
    },
    {
        "code": "so_credit",
        "category": "commercial",
        "label": "Nota de crédito",
        "tooltip": "Permite emitir notas de crédito fiscales.",
        "xmlids": ("l10n_do_accounting.group_l10n_do_fiscal_credit_note",),
    },
    {
        "code": "so_discount",
        "category": "commercial",
        "label": "Aplicar descuentos",
        "tooltip": "Permite aplicar descuentos en líneas de venta.",
        "xmlids": ("sale.group_discount_per_so_line",),
    },
    {
        "code": "so_delete_inv",
        "category": "commercial",
        "label": "Eliminar factura",
        "tooltip": "Permite eliminar facturas en estados autorizados (Administrador).",
        "xmlids": ("account.group_account_manager",),
    },
    {
        "code": "so_edit_posted",
        "category": "commercial",
        "label": "Modificar factura validada",
        "tooltip": (
            "Permite operaciones administrativas sobre facturas publicadas "
            "cuando Odoo lo autoriza (Administrador)."
        ),
        "xmlids": ("account.group_account_manager",),
    },
    # Inventario
    {
        "code": "stk_in",
        "category": "inventory",
        "label": "Entradas",
        "tooltip": "Permite registrar entradas de inventario.",
        "xmlids": ("stock.group_stock_user",),
    },
    {
        "code": "stk_out",
        "category": "inventory",
        "label": "Salidas",
        "tooltip": "Permite registrar salidas de inventario.",
        "xmlids": ("stock.group_stock_user",),
    },
    {
        "code": "stk_adj",
        "category": "inventory",
        "label": "Ajustes",
        "tooltip": "Permite realizar ajustes de inventario.",
        "xmlids": ("stock.group_stock_user",),
    },
    {
        "code": "stk_tr",
        "category": "inventory",
        "label": "Transferencias",
        "tooltip": "Permite transferencias entre ubicaciones.",
        "xmlids": ("stock.group_stock_user",),
    },
    {
        "code": "stk_count",
        "category": "inventory",
        "label": "Conteos",
        "tooltip": "Permite conteos/inventarios físicos.",
        "xmlids": ("stock.group_stock_user",),
    },
    {
        "code": "stk_val",
        "category": "inventory",
        "label": "Valoración",
        "tooltip": "Permite administrar valoración (Administrador de inventario).",
        "xmlids": ("stock.group_stock_manager",),
    },
    # Fiscal actions extras
    {
        "code": "fis_void",
        "category": "fiscal",
        "label": "Anular NCF",
        "tooltip": (
            "Permite anular comprobantes fiscales. No cancela pagos ni emite "
            "nota de crédito automáticamente."
        ),
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_manager",),
    },
    {
        "code": "fis_606",
        "category": "fiscal",
        "label": "Generar 606",
        "tooltip": "Permite generar el formato 606.",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fis_607",
        "category": "fiscal",
        "label": "Generar 607",
        "tooltip": "Permite generar el formato 607.",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fis_608",
        "category": "fiscal",
        "label": "Generar 608",
        "tooltip": "Permite generar el formato 608.",
        "xmlids": ("justech_l10n_do_base.group_justech_do_fiscal_user",),
    },
    {
        "code": "fis_ranges",
        "category": "fiscal",
        "label": "Configurar rangos",
        "tooltip": "Permite administrar rangos NCF.",
        "xmlids": ("justech_fiscal_admin.group_justech_fiscal_admin_manager",),
    },
    # Garantías
    {
        "code": "war_create",
        "category": "warranty",
        "label": "Crear garantía",
        "tooltip": "Permite crear garantías.",
        "xmlids": ("justech_warranty.group_warranty_user",),
    },
    {
        "code": "war_edit",
        "category": "warranty",
        "label": "Modificar garantía",
        "tooltip": "Permite modificar garantías existentes.",
        "xmlids": ("justech_warranty.group_warranty_user",),
    },
    {
        "code": "war_process",
        "category": "warranty",
        "label": "Procesar garantía",
        "tooltip": "Permite procesar/aprobar garantías.",
        "xmlids": ("justech_warranty.group_warranty_manager",),
    },
    {
        "code": "war_history",
        "category": "warranty",
        "label": "Consultar historial",
        "tooltip": "Permite consultar el historial de garantías.",
        "xmlids": ("justech_warranty.group_warranty_user",),
    },
)
