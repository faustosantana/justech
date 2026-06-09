"""Enumeraciones Work Operations Center."""

from enum import Enum


class TaskStatus(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    ESPERANDO_TERCERO = "esperando_tercero"
    EN_REVISION = "en_revision"
    COMPLETADA = "completada"
    VENCIDA = "vencida"
    CANCELADA = "cancelada"


class TaskPriority(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class TaskCategory(str, Enum):
    COTIZACION = "cotizacion"
    FACTURA_CLIENTE = "factura_cliente"
    FACTURA_PROVEEDOR = "factura_proveedor"
    PAGO_CLIENTE = "pago_cliente"
    CUENTA_POR_COBRAR = "cuenta_por_cobrar"
    CUENTA_POR_PAGAR = "cuenta_por_pagar"
    LICITACION = "licitacion"
    SOPORTE = "soporte"
    COMPRA = "compra"
    ENTREGA = "entrega"
    ADMINISTRACION = "administracion"
    FINANZAS = "finanzas"
    VENTAS = "ventas"
    PROYECTO = "proyecto"
    DOCUMENTO = "documento"
    SEGUIMIENTO_CLIENTE = "seguimiento_cliente"
    OTRO = "otro"


class TaskDepartment(str, Enum):
    VENTAS = "ventas"
    FACTURACION = "facturacion"
    FINANZAS = "finanzas"
    ADMINISTRACION = "administracion"
    SOPORTE = "soporte"
    OPERACIONES = "operaciones"
    COMPRAS = "compras"
    GERENCIA = "gerencia"
    LICITACIONES = "licitaciones"


class TaskSource(str, Enum):
    MANUAL = "manual"
    M365_EMAIL = "m365_email"
    ODOO_INVOICE = "odoo_invoice"
    ODOO_CUSTOMER = "odoo_customer"
    ODOO_QUOTATION = "odoo_quotation"
    ODOO_OPPORTUNITY = "odoo_opportunity"
    ODOO_PROJECT = "odoo_project"
    DGCP_OPPORTUNITY = "dgcp_opportunity"
    SUPPORT_TICKET = "support_ticket"
    ASSISTANT = "assistant"
    EVENT = "event"
    PRICE_INTELLIGENCE = "price_intelligence"


class NotificationType(str, Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_REASSIGNED = "task_reassigned"
    TASK_DUE_SOON = "task_due_soon"
    TASK_OVERDUE = "task_overdue"
    TASK_COMPLETED = "task_completed"
    TASK_UPDATED = "task_updated"
    TASK_COMMENTED = "task_commented"
    INVOICE_FOLLOWUP = "invoice_followup"
    QUOTATION_FOLLOWUP = "quotation_followup"
    DGCP_DEADLINE = "dgcp_deadline"
    SUPPORT_ESCALATION = "support_escalation"
    SYSTEM_ALERT = "system_alert"


class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
