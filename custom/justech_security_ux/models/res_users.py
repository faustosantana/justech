# -*- coding: utf-8 -*-
"""Permisos operativos: representación amigable de res.groups (bidireccional)."""
from odoo import api, fields, models

from .operational_permissions_registry import (
    OPERATIONAL_CATEGORIES,
    OPERATIONAL_PERMISSIONS,
)


def _op_field_name(code):
    return f"op_perm_{code}"


class ResUsers(models.Model):
    _inherit = "res.users"

    op_perm_summary_can = fields.Text(
        string="Puede",
        compute="_compute_op_perm_summary",
    )
    op_perm_summary_cannot = fields.Text(
        string="No puede",
        compute="_compute_op_perm_summary",
    )
    op_perm_help = fields.Char(
        string="Ayuda permisos operativos",
        default=(
            "Estos interruptores activan o desactivan grupos reales de Odoo. "
            "No hay una segunda capa de ACL. Si un permiso no se puede apagar, "
            "un grupo superior (p. ej. Administrador del sistema) lo mantiene activo."
        ),
    )

    # --- CONTABILIDAD ---
    op_perm_acc_view = fields.Boolean(
        string="Ver contabilidad",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite consultar asientos, diarios y reportes contables en solo lectura.\n\n"
            "No permite: crear o publicar asientos; cancelar asientos; "
            "administrar configuración contable."
        ),
    )
    op_perm_acc_create = fields.Boolean(
        string="Crear asientos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite crear asientos y trabajar con la contabilidad operativa.\n\n"
            "No permite: administrar configuración contable avanzada; "
            "eliminar con privilegios de administrador."
        ),
    )
    op_perm_acc_post = fields.Boolean(
        string="Publicar asientos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite publicar asientos contables dentro de las reglas estándar de Odoo.\n\n"
            "Comparte el mismo grupo técnico que «Crear asientos».\n\n"
            "No permite: saltarse bloqueos de diarios o inalterabilidad."
        ),
    )
    op_perm_acc_cancel = fields.Boolean(
        string="Cancelar asientos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite cancelar asientos cuando el diario y el estado del documento lo permiten.\n\n"
            "No permite: anular NCF; romper conciliaciones fuera del flujo estándar."
        ),
    )
    op_perm_acc_delete_draft = fields.Boolean(
        string="Eliminar borradores",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite eliminar borradores contables con privilegios de Administrador contable.\n\n"
            "No permite: eliminar asientos publicados; alterar histórico publicado."
        ),
    )

    # --- PAGOS ---
    op_perm_pay_view = fields.Boolean(
        string="Ver pagos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite ver pagos y documentos de facturación relacionados.\n\n"
            "No permite: registrar o aplicar pagos; cancelar o eliminar pagos."
        ),
    )
    op_perm_pay_register = fields.Boolean(
        string="Registrar pagos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite registrar pagos desde el flujo de facturación/pagos de Odoo.\n\n"
            "No permite: eliminar pagos; administrar diarios bancarios."
        ),
    )
    op_perm_pay_apply = fields.Boolean(
        string="Aplicar pagos a facturas",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite registrar y aplicar pagos a facturas abiertas.\n\n"
            "No permite: eliminar pagos; cancelar pagos fuera del flujo estándar; "
            "modificar diarios; modificar asientos publicados."
        ),
    )
    op_perm_pay_reconcile = fields.Boolean(
        string="Conciliar pagos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite conciliar movimientos bancarios/contables con la contabilidad operativa.\n\n"
            "No permite: administrar bancos sin el permiso específico."
        ),
    )
    op_perm_pay_unreconcile = fields.Boolean(
        string="Desconciliar",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite desconciliar cuando Odoo lo permite en el documento.\n\n"
            "No permite: forzar desconciliación sobre asientos bloqueados."
        ),
    )
    op_perm_pay_cancel = fields.Boolean(
        string="Cancelar pagos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite cancelar pagos según las reglas estándar del documento.\n\n"
            "No permite: eliminar pagos definitivos como Administrador; alterar NCF."
        ),
    )
    op_perm_pay_delete = fields.Boolean(
        string="Eliminar pagos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite eliminar pagos en estados que Odoo autorice al Administrador contable.\n\n"
            "No permite: borrar pagos conciliados bloqueados."
        ),
    )
    op_perm_pay_bank_admin = fields.Boolean(
        string="Administrar diarios bancarios",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite validar/administrar cuentas bancarias.\n\n"
            "No permite por sí solo: publicar facturas; anular NCF."
        ),
    )

    # --- FACTURACIÓN ---
    op_perm_inv_view = fields.Boolean(
        string="Ver facturas",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite ver facturas de cliente/proveedor.\n\n"
            "No permite: publicar; cancelar fiscales; emitir notas de crédito fiscales."
        ),
    )
    op_perm_inv_create = fields.Boolean(
        string="Crear facturas",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite crear facturas en borrador.\n\n"
            "No permite: cancelar facturas fiscales sin permiso específico; anular NCF."
        ),
    )
    op_perm_inv_edit_draft = fields.Boolean(
        string="Editar borradores",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite editar facturas en borrador.\n\n"
            "No permite: modificar facturas publicadas."
        ),
    )
    op_perm_inv_post = fields.Boolean(
        string="Publicar facturas",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite publicar facturas y consumir NCF según Motor Fiscal.\n\n"
            "No permite: anular NCF; administrar rangos."
        ),
    )
    op_perm_inv_cancel = fields.Boolean(
        string="Cancelar facturas",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite cancelar facturas fiscales (grupo l10n_do).\n\n"
            "No permite: anular NCF; borrar histórico."
        ),
    )
    op_perm_inv_credit_note = fields.Boolean(
        string="Nota de crédito",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite crear notas de crédito fiscales.\n\n"
            "No permite: anular NCF como sustituto de NC; administrar rangos."
        ),
    )

    # --- COMPRAS ---
    op_perm_po_create = fields.Boolean(
        string="Crear solicitudes",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite crear solicitudes/órdenes de compra.\n\n"
            "No permite: administrar compras como Administrador."
        ),
    )
    op_perm_po_approve = fields.Boolean(
        string="Aprobar compras",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite aprobar y administrar el flujo de compras.\n\n"
            "No permite: publicar facturas sin permiso de facturación."
        ),
    )
    op_perm_po_confirm = fields.Boolean(
        string="Confirmar órdenes",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite confirmar órdenes de compra (Usuario de Compras).",
    )
    op_perm_po_bill = fields.Boolean(
        string="Facturar compras",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite generar/procesar facturas de proveedor.\n\n"
            "No permite: administrar rangos NCF de compras emitidas."
        ),
    )
    op_perm_po_received = fields.Boolean(
        string="Administrar documentos recibidos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite operar compras con documentos recibidos (Usuario Fiscal).\n\n"
            "No permite: anular NCF; administrar rangos."
        ),
    )
    op_perm_po_issued = fields.Boolean(
        string="Administrar documentos emitidos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite emitir comprobantes de compra Justech (Responsable Fiscal).\n\n"
            "No permite: administrar padrón/rangos como Administrador Fiscal."
        ),
    )

    # --- FISCAL ---
    op_perm_fis_rnc = fields.Boolean(
        string="Validar RNC",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite validar/consultar RNC (Usuario Fiscal).\n\n"
            "No permite: anular NCF; administrar rangos."
        ),
    )
    op_perm_fis_docs = fields.Boolean(
        string="Seleccionar comprobantes",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite seleccionar tipos de comprobante (Usuario Fiscal).",
    )
    op_perm_fis_void_ncf = fields.Boolean(
        string="Anular NCF",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite anular comprobantes fiscales (Responsable Fiscal) vía wizard 608.\n\n"
            "No permite: necesariamente cancelar asientos; emitir NC automáticamente; "
            "devolver pagos."
        ),
    )
    op_perm_fis_606 = fields.Boolean(
        string="Generar 606",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite generar/consultar el formato 606 (Usuario Fiscal).",
    )
    op_perm_fis_607 = fields.Boolean(
        string="Generar 607",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite generar/consultar el formato 607 (Usuario Fiscal).",
    )
    op_perm_fis_608 = fields.Boolean(
        string="Generar 608",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite generar/consultar el formato 608 (Usuario Fiscal).",
    )
    op_perm_fis_ranges = fields.Boolean(
        string="Administrar rangos",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite administrar rangos NCF y consola fiscal (Administrador Fiscal).\n\n"
            "No otorga permisos contables generales por sí solo."
        ),
    )
    op_perm_fis_ecf = fields.Boolean(
        string="Administrar e-CF",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help=(
            "Permite operar/administrar e-CF (Administrador e-CF).\n\n"
            "No permite: alterar NCF tradicionales fuera de e-CF."
        ),
    )

    # --- RETENCIONES ---
    op_perm_wh_register = fields.Boolean(
        string="Registrar",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite registrar retenciones en el flujo de pagos/facturación.",
    )
    op_perm_wh_apply = fields.Boolean(
        string="Aplicar",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite aplicar retenciones en pagos (Facturación).",
    )
    op_perm_wh_approve = fields.Boolean(
        string="Aprobar",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite aprobar/gestionar retenciones (Administrador contable).",
    )
    op_perm_wh_admin = fields.Boolean(
        string="Administrar",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite administrar el catálogo de retenciones Justech.",
    )

    # --- GARANTÍAS ---
    op_perm_war_create = fields.Boolean(
        string="Crear",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite crear garantías (Usuario de Garantías).",
    )
    op_perm_war_edit = fields.Boolean(
        string="Editar",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite editar garantías (Usuario de Garantías).",
    )
    op_perm_war_approve = fields.Boolean(
        string="Aprobar",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite aprobar/gestionar garantías (Responsable de Garantías).",
    )
    op_perm_war_admin = fields.Boolean(
        string="Administrar",
        compute="_compute_op_permissions",
        inverse="_inverse_op_permissions",
        help="Permite administrar configuración de garantías (Responsable de Garantías).",
    )

    # ------------------------------------------------------------------ registry
    @api.model
    def _op_perm_registry(self):
        return OPERATIONAL_PERMISSIONS

    @api.model
    def _op_perm_categories(self):
        return OPERATIONAL_CATEGORIES

    @api.model
    def _op_perm_item(self, code):
        for item in self._op_perm_registry():
            if item["code"] == code:
                return item
        return None

    @api.model
    def _op_perm_resolve_groups(self, item):
        groups = self.env["res.groups"]
        if not item:
            return groups
        for xmlid in item.get("xmlids") or ():
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    @api.model
    def _op_perm_managed_groups(self):
        groups = self.env["res.groups"]
        for item in self._op_perm_registry():
            groups |= self._op_perm_resolve_groups(item)
        return groups

    def _op_perm_user_has_item(self, user, item):
        groups = self._op_perm_resolve_groups(item)
        if not groups:
            return False
        # has_group incluye implicaciones: refleja el estado real de seguridad.
        return all(user.has_group(xmlid) for xmlid in item["xmlids"] if self.env.ref(xmlid, raise_if_not_found=False))

    @api.depends("group_ids")
    def _compute_op_permissions(self):
        for user in self:
            for item in self._op_perm_registry():
                fname = _op_field_name(item["code"])
                if fname in user._fields:
                    user[fname] = user._op_perm_user_has_item(user, item)

    @api.depends(
        *[
            _op_field_name(item["code"])
            for item in OPERATIONAL_PERMISSIONS
        ]
    )
    def _compute_op_perm_summary(self):
        for user in self:
            can_lines = []
            cannot_lines = []
            for item in self._op_perm_registry():
                fname = _op_field_name(item["code"])
                if fname not in user._fields:
                    continue
                label = item["label"]
                if user[fname]:
                    can_lines.append("✔ %s" % label)
                else:
                    cannot_lines.append("✘ %s" % label)
            user.op_perm_summary_can = "\n".join(can_lines) if can_lines else "—"
            user.op_perm_summary_cannot = (
                "\n".join(cannot_lines) if cannot_lines else "—"
            )

    def _inverse_op_permissions(self):
        for user in self:
            user._op_perm_sync_from_fields()

    def _op_perm_sync_from_fields(self):
        """Aplica membresía de grupos gestionados según checkboxes operativos."""
        self.ensure_one()
        managed = self._op_perm_managed_groups()
        if not managed:
            return
        desired = self.env["res.groups"]
        for item in self._op_perm_registry():
            fname = _op_field_name(item["code"])
            if fname in self._fields and self[fname]:
                desired |= self._op_perm_resolve_groups(item)

        commands = []
        for group in managed:
            has_explicit = group in self.group_ids
            want = group in desired
            if want and not has_explicit:
                commands.append((4, group.id))
            elif not want and has_explicit:
                commands.append((3, group.id))

        if commands:
            self.with_context(justech_security_ux_sync=True).write(
                {"group_ids": commands}
            )
