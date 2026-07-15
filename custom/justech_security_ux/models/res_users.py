# -*- coding: utf-8 -*-
"""UX Enterprise de permisos — sincroniza únicamente res.groups existentes."""
from odoo import api, fields, models

from .enterprise_permissions_registry import (
    ENTERPRISE_ACTIONS,
    ENTERPRISE_CATEGORIES,
    ENTERPRISE_ROLES,
)


def _act_fname(code):
    return f"op_act_{code}"


def _role_fname(category):
    return f"op_role_{category}"


class ResUsers(models.Model):
    _inherit = "res.users"

    op_enterprise_help = fields.Char(
        string="Ayuda",
        default=(
            "Active una o varias áreas. Cada área es independiente: "
            "cambiar Compras no altera Ventas ni Fiscal. "
            "Los cambios sincronizan grupos reales de Odoo."
        ),
    )
    op_summary_areas = fields.Text(
        string="Áreas activas", compute="_compute_op_summary_global"
    )
    op_summary_can = fields.Text(string="Puede", compute="_compute_op_summary_global")
    op_summary_cannot = fields.Text(string="No puede", compute="_compute_op_summary_global")

    # Intención de abrir área (permite ver el bloque sin grupos aún)
    op_area_open_commercial = fields.Boolean(string="Abrir Comercial", default=False)
    op_area_open_purchase = fields.Boolean(string="Abrir Compras", default=False)
    op_area_open_inventory = fields.Boolean(string="Abrir Inventario", default=False)
    op_area_open_finance = fields.Boolean(string="Abrir Finanzas", default=False)
    op_area_open_accounting = fields.Boolean(string="Abrir Contabilidad", default=False)
    op_area_open_fiscal = fields.Boolean(string="Abrir Fiscal", default=False)
    op_area_open_ecf = fields.Boolean(string="Abrir e-CF", default=False)
    op_area_open_warranty = fields.Boolean(string="Abrir Garantías", default=False)
    op_area_open_hr = fields.Boolean(string="Abrir RRHH", default=False)
    op_area_open_crm = fields.Boolean(string="Abrir CRM", default=False)
    op_area_open_admin = fields.Boolean(string="Abrir Administración", default=False)

    # Checkbox de área = abierta o con membresía efectiva
    op_area_commercial = fields.Boolean(
        string="Comercial",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_purchase = fields.Boolean(
        string="Compras",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_inventory = fields.Boolean(
        string="Inventario",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_finance = fields.Boolean(
        string="Finanzas",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_accounting = fields.Boolean(
        string="Contabilidad",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_fiscal = fields.Boolean(
        string="Fiscal",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_ecf = fields.Boolean(
        string="e-CF",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_warranty = fields.Boolean(
        string="Garantías",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_hr = fields.Boolean(
        string="Recursos Humanos",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_crm = fields.Boolean(
        string="CRM",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )
    op_area_admin = fields.Boolean(
        string="Administración Justech",
        compute="_compute_op_areas",
        inverse="_inverse_op_areas",
    )

    # Tarjetas de rol por área (independientes)
    op_role_card_commercial = fields.Text(compute="_compute_op_role_cards")
    op_role_card_purchase = fields.Text(compute="_compute_op_role_cards")
    op_role_card_inventory = fields.Text(compute="_compute_op_role_cards")
    op_role_card_finance = fields.Text(compute="_compute_op_role_cards")
    op_role_card_accounting = fields.Text(compute="_compute_op_role_cards")
    op_role_card_fiscal = fields.Text(compute="_compute_op_role_cards")
    op_role_card_ecf = fields.Text(compute="_compute_op_role_cards")
    op_role_card_warranty = fields.Text(compute="_compute_op_role_cards")
    op_role_card_hr = fields.Text(compute="_compute_op_role_cards")
    op_role_card_crm = fields.Text(compute="_compute_op_role_cards")
    op_role_card_admin = fields.Text(compute="_compute_op_role_cards")

    # Roles por categoría
    op_role_commercial = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("commercial_own", "Usuario"),
            ("commercial_all", "Supervisor"),
            ("commercial_admin", "Administrador"),
        ],
        string="Rol comercial",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_purchase = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("purchase_user", "Usuario"),
            ("purchase_admin", "Administrador"),
        ],
        string="Rol compras",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_inventory = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("inventory_user", "Usuario"),
            ("inventory_admin", "Administrador"),
        ],
        string="Rol inventario",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_finance = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("finance_invoice", "Usuario"),
            ("finance_book", "Supervisor"),
            ("finance_admin", "Administrador"),
        ],
        string="Rol finanzas",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_accounting = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("accounting_ro", "Usuario"),
            ("accounting_ops", "Supervisor"),
            ("accounting_admin", "Administrador"),
        ],
        string="Rol contabilidad",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_fiscal = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("fiscal_user", "Usuario"),
            ("fiscal_officer", "Supervisor"),
            ("fiscal_admin", "Administrador"),
        ],
        string="Rol fiscal",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_ecf = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("ecf_ro", "Usuario"),
            ("ecf_op", "Supervisor"),
            ("ecf_resp", "Responsable"),
            ("ecf_admin", "Administrador"),
        ],
        string="Rol e-CF",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_warranty = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("warranty_user", "Usuario"),
            ("warranty_admin", "Administrador"),
        ],
        string="Rol garantías",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_hr = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("hr_user", "Usuario"),
            ("hr_admin", "Administrador"),
        ],
        string="Rol RRHH",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_crm = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("crm_leads", "Usuario"),
        ],
        string="Rol CRM",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )
    op_role_admin = fields.Selection(
        selection=[
            ("none", "Sin rol"),
            ("admin_user", "Usuario"),
            ("admin_manager", "Administrador"),
        ],
        string="Rol Administración Justech",
        compute="_compute_op_roles",
        inverse="_inverse_op_enterprise",
    )

    # Acciones (booleans) — nombres humanos
    op_act_fin_register_in = fields.Boolean(
        string="Registrar cobros",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite registrar cobros de clientes. No permite eliminar pagos.",
    )
    op_act_fin_register_out = fields.Boolean(
        string="Registrar pagos",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite registrar pagos a proveedores. No permite eliminarlos.",
    )
    op_act_fin_apply = fields.Boolean(
        string="Aplicar pagos",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite aplicar pagos registrados a facturas existentes. No permite eliminarlos.",
    )
    op_act_fin_reconcile = fields.Boolean(
        string="Reconciliar",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite conciliar movimientos bancarios y contables.",
    )
    op_act_fin_unreconcile = fields.Boolean(
        string="Desconciliar",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite desconciliar cuando el documento lo permite.",
    )
    op_act_fin_approve = fields.Boolean(
        string="Aprobar pagos",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite aprobar/gestionar pagos con privilegio administrador.",
    )
    op_act_fin_bank_create = fields.Boolean(
        string="Crear diarios",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite administrar diarios/cuentas bancarias (validación bancaria).",
    )
    op_act_fin_bank_edit = fields.Boolean(
        string="Modificar diarios",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite modificar configuración bancaria autorizada.",
    )
    op_act_fin_export = fields.Boolean(
        string="Exportar",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite exportar información financiera según permisos de Odoo.",
    )
    op_act_fin_reports = fields.Boolean(
        string="Ver reportes",
        compute="_compute_op_actions",
        inverse="_inverse_op_enterprise",
        help="Permite consultar reportes de facturación y pagos.",
    )

    op_act_po_request = fields.Boolean(
        string="Crear solicitud", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite crear solicitudes de compra.",
    )
    op_act_po_approve_req = fields.Boolean(
        string="Aprobar solicitud", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite aprobar solicitudes (Administrador de compras).",
    )
    op_act_po_order = fields.Boolean(
        string="Crear orden", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite crear órdenes de compra.",
    )
    op_act_po_approve_order = fields.Boolean(
        string="Aprobar orden", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite aprobar órdenes de compra.",
    )
    op_act_po_vendor_bill = fields.Boolean(
        string="Registrar factura proveedor", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite registrar facturas de proveedor.",
    )
    op_act_po_received = fields.Boolean(
        string="Registrar documento recibido", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite registrar compras con NCF recibido del proveedor.",
    )
    op_act_po_b11 = fields.Boolean(
        string="Emitir B11", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite emitir comprobantes de compra B11 (Responsable Fiscal).",
    )
    op_act_po_b13 = fields.Boolean(
        string="Emitir B13", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite emitir comprobantes de compra B13 (Responsable Fiscal).",
    )
    op_act_po_b17 = fields.Boolean(
        string="Emitir B17", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite emitir comprobantes de compra B17 (Responsable Fiscal).",
    )
    op_act_po_cancel = fields.Boolean(
        string="Cancelar orden", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite cancelar órdenes según el flujo estándar.",
    )
    op_act_po_delete = fields.Boolean(
        string="Eliminar orden", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite eliminar órdenes en estados autorizados (Administrador).",
    )

    op_act_so_quote = fields.Boolean(
        string="Crear cotización", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite crear cotizaciones de venta.",
    )
    op_act_so_approve = fields.Boolean(
        string="Aprobar cotización", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite aprobar cotizaciones (Administrador comercial).",
    )
    op_act_so_confirm = fields.Boolean(
        string="Confirmar venta", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite confirmar pedidos de venta.",
    )
    op_act_so_invoice = fields.Boolean(
        string="Emitir factura", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite emitir facturas desde ventas/facturación.",
    )
    op_act_so_credit = fields.Boolean(
        string="Nota de crédito", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite emitir notas de crédito fiscales.",
    )
    op_act_so_discount = fields.Boolean(
        string="Aplicar descuentos", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite aplicar descuentos en líneas de venta.",
    )
    op_act_so_delete_inv = fields.Boolean(
        string="Eliminar factura", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite eliminar facturas en estados autorizados (Administrador).",
    )
    op_act_so_edit_posted = fields.Boolean(
        string="Modificar factura validada", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite operaciones administrativas sobre facturas publicadas cuando Odoo lo autoriza.",
    )

    op_act_stk_in = fields.Boolean(
        string="Entradas", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite registrar entradas de inventario.",
    )
    op_act_stk_out = fields.Boolean(
        string="Salidas", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite registrar salidas de inventario.",
    )
    op_act_stk_adj = fields.Boolean(
        string="Ajustes", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite realizar ajustes de inventario.",
    )
    op_act_stk_tr = fields.Boolean(
        string="Transferencias", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite transferencias entre ubicaciones.",
    )
    op_act_stk_count = fields.Boolean(
        string="Conteos", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite conteos/inventarios físicos.",
    )
    op_act_stk_val = fields.Boolean(
        string="Valoración", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite administrar valoración (Administrador de inventario).",
    )

    op_act_fis_void = fields.Boolean(
        string="Anular NCF", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite anular comprobantes fiscales. No cancela pagos ni emite nota de crédito automáticamente.",
    )
    op_act_fis_606 = fields.Boolean(
        string="Generar 606", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite generar el formato 606.",
    )
    op_act_fis_607 = fields.Boolean(
        string="Generar 607", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite generar el formato 607.",
    )
    op_act_fis_608 = fields.Boolean(
        string="Generar 608", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite generar el formato 608.",
    )
    op_act_fis_ranges = fields.Boolean(
        string="Configurar rangos", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite administrar rangos NCF.",
    )

    op_act_war_create = fields.Boolean(
        string="Crear garantía", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite crear garantías.",
    )
    op_act_war_edit = fields.Boolean(
        string="Modificar garantía", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite modificar garantías existentes.",
    )
    op_act_war_process = fields.Boolean(
        string="Procesar garantía", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite procesar/aprobar garantías.",
    )
    op_act_war_history = fields.Boolean(
        string="Consultar historial", compute="_compute_op_actions", inverse="_inverse_op_enterprise",
        help="Permite consultar el historial de garantías.",
    )

    # ------------------------------------------------------------------ helpers
    @api.model
    def _op_categories(self):
        return ENTERPRISE_CATEGORIES

    @api.model
    def _op_roles(self):
        return ENTERPRISE_ROLES

    @api.model
    def _op_actions(self):
        return ENTERPRISE_ACTIONS

    @api.model
    def _op_role_by_code(self, code):
        for role in ENTERPRISE_ROLES:
            if role["code"] == code:
                return role
        return None

    @api.model
    def _op_resolve_xmlids(self, xmlids):
        groups = self.env["res.groups"]
        for xmlid in xmlids or ():
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    @api.model
    def _op_managed_groups(self):
        groups = self.env["res.groups"]
        for role in ENTERPRISE_ROLES:
            groups |= self._op_resolve_xmlids(role["xmlids"])
        for act in ENTERPRISE_ACTIONS:
            groups |= self._op_resolve_xmlids(act["xmlids"])
        return groups

    def _op_user_has_xmlids(self, user, xmlids):
        for xmlid in xmlids or ():
            if not self.env.ref(xmlid, raise_if_not_found=False):
                return False
            if not user.has_group(xmlid):
                return False
        return bool(xmlids)

    def _op_detect_role(self, user, category):
        best = "none"
        best_level = 0
        for role in ENTERPRISE_ROLES:
            if role["category"] != category:
                continue
            if self._op_user_has_xmlids(user, role["xmlids"]) and role["level"] >= best_level:
                best = role["code"]
                best_level = role["level"]
        return best

    def _op_category_action_codes(self, category):
        return [a["code"] for a in ENTERPRISE_ACTIONS if a["category"] == category]

    def _op_category_has_membership(self, user, category):
        role_fname = _role_fname(category)
        if role_fname in user._fields and user[role_fname] not in (False, "none"):
            return True
        for code in self._op_category_action_codes(category):
            fname = _act_fname(code)
            if fname in user._fields and user[fname]:
                return True
        return False

    @api.depends("group_ids")
    def _compute_op_roles(self):
        cats = [c["key"] for c in ENTERPRISE_CATEGORIES]
        for user in self:
            for cat in cats:
                fname = _role_fname(cat)
                if fname in user._fields:
                    user[fname] = user._op_detect_role(user, cat)

    @api.depends("group_ids")
    def _compute_op_actions(self):
        for user in self:
            for act in ENTERPRISE_ACTIONS:
                fname = _act_fname(act["code"])
                if fname in user._fields:
                    user[fname] = user._op_user_has_xmlids(user, act["xmlids"])

    @api.depends(
        "group_ids",
        "op_area_open_commercial",
        "op_area_open_purchase",
        "op_area_open_inventory",
        "op_area_open_finance",
        "op_area_open_accounting",
        "op_area_open_fiscal",
        "op_area_open_ecf",
        "op_area_open_warranty",
        "op_area_open_hr",
        "op_area_open_crm",
        "op_area_open_admin",
        "op_role_commercial",
        "op_role_purchase",
        "op_role_inventory",
        "op_role_finance",
        "op_role_accounting",
        "op_role_fiscal",
        "op_role_ecf",
        "op_role_warranty",
        "op_role_hr",
        "op_role_crm",
        "op_role_admin",
    )
    def _compute_op_areas(self):
        for user in self:
            for cat in (c["key"] for c in ENTERPRISE_CATEGORIES):
                open_fname = "op_area_open_%s" % cat
                area_fname = "op_area_%s" % cat
                opened = bool(user[open_fname]) if open_fname in user._fields else False
                user[area_fname] = opened or user._op_category_has_membership(user, cat)

    def _inverse_op_areas(self):
        """Activar/desactivar área sin afectar otras áreas."""
        for user in self:
            # Evitar sync parcial por cada assignment de op_role/op_act.
            u = user.with_context(justech_security_ux_skip_sync=True)
            for cat in (c["key"] for c in ENTERPRISE_CATEGORIES):
                area_fname = "op_area_%s" % cat
                open_fname = "op_area_open_%s" % cat
                if area_fname not in u._fields:
                    continue
                if u[area_fname]:
                    u[open_fname] = True
                    continue
                # Desactivar solo esta área
                u[open_fname] = False
                role_fname = _role_fname(cat)
                if role_fname in u._fields:
                    u[role_fname] = "none"
                for code in u._op_category_action_codes(cat):
                    fname = _act_fname(code)
                    if fname in u._fields:
                        u[fname] = False
            user._op_sync_enterprise()

    @api.depends(
        "op_role_commercial",
        "op_role_purchase",
        "op_role_inventory",
        "op_role_finance",
        "op_role_accounting",
        "op_role_fiscal",
        "op_role_ecf",
        "op_role_warranty",
        "op_role_hr",
        "op_role_crm",
        "op_role_admin",
    )
    def _compute_op_role_cards(self):
        for user in self:
            for cat in (c["key"] for c in ENTERPRISE_CATEGORIES):
                card_fname = "op_role_card_%s" % cat
                if card_fname not in user._fields:
                    continue
                role_code = user[_role_fname(cat)] if _role_fname(cat) in user._fields else "none"
                role = self._op_role_by_code(role_code) if role_code and role_code != "none" else None
                if not role:
                    user[card_fname] = "Sin rol seleccionado en esta área."
                    continue
                lines = [role["label"], ""]
                lines.extend("• %s" % b for b in role["bullets"])
                user[card_fname] = "\n".join(lines)

    @api.depends("group_ids", "op_area_commercial", "op_area_purchase", "op_area_inventory",
                 "op_area_finance", "op_area_accounting", "op_area_fiscal", "op_area_ecf",
                 "op_area_warranty", "op_area_hr", "op_area_crm", "op_area_admin")
    def _compute_op_summary_global(self):
        label_by_cat = {c["key"]: c["label"] for c in ENTERPRISE_CATEGORIES}
        for user in self:
            active = []
            can, cannot = [], []
            for cat in (c["key"] for c in ENTERPRISE_CATEGORIES):
                area_fname = "op_area_%s" % cat
                area_on = area_fname in user._fields and user[area_fname]
                if area_on:
                    active.append("✓ %s" % label_by_cat[cat])
                for act in ENTERPRISE_ACTIONS:
                    if act["category"] != cat:
                        continue
                    fname = _act_fname(act["code"])
                    if fname not in user._fields:
                        continue
                    label = "%s — %s" % (label_by_cat[cat], act["label"])
                    if user[fname]:
                        can.append("• %s" % label)
                    elif area_on:
                        # Solo listar «no puede» de áreas activas
                        cannot.append("• %s" % label)
            user.op_summary_areas = "\n".join(active) if active else "—"
            user.op_summary_can = "\n".join(can) if can else "—"
            user.op_summary_cannot = "\n".join(cannot) if cannot else "—"

    def _inverse_op_enterprise(self):
        if self.env.context.get("justech_security_ux_skip_sync"):
            return
        for user in self:
            user._op_sync_enterprise()

    def _op_sync_enterprise(self):
        """Sincroniza grupos gestionados; cada área aporta independientemente."""
        self.ensure_one()
        managed = self._op_managed_groups()
        if not managed:
            return
        desired = self.env["res.groups"]

        for cat in (c["key"] for c in ENTERPRISE_CATEGORIES):
            fname = _role_fname(cat)
            if fname not in self._fields:
                continue
            code = self[fname]
            if not code or code == "none":
                continue
            role = self._op_role_by_code(code)
            if role:
                desired |= self._op_resolve_xmlids(role["xmlids"])

        for act in ENTERPRISE_ACTIONS:
            fname = _act_fname(act["code"])
            if fname in self._fields and self[fname]:
                desired |= self._op_resolve_xmlids(act["xmlids"])

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
