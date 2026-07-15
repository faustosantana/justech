# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JustechManagedService(models.Model):
    _name = "justech.managed.service"
    _description = "Servicio Administrado / Iguala"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        default=lambda self: _("Nuevo"),
        readonly=True,
        tracking=True,
    )
    title = fields.Char(
        string="Nombre del servicio",
        required=True,
        tracking=True,
        help="Nombre comercial de la iguala o servicio administrado.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        tracking=True,
        index=True,
        domain="[('is_company', '=', True)]",
    )
    contact_id = fields.Many2one(
        "res.partner",
        string="Contacto principal",
        domain="[('parent_id', '=', partner_id), ('is_company', '=', False)]",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa prestadora",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    salesperson_id = fields.Many2one(
        "res.users",
        string="Comercial responsable",
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    technician_id = fields.Many2one(
        "res.users",
        string="Responsable técnico",
        tracking=True,
        index=True,
    )
    opportunity_id = fields.Many2one(
        "crm.lead",
        string="Oportunidad CRM",
        index=True,
        tracking=True,
    )
    assessment_id = fields.Many2one(
        "justech.managed.service.assessment",
        string="Levantamiento de origen",
        index=True,
        tracking=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Cotización / Pedido",
        index=True,
        tracking=True,
        domain="[('partner_id', 'child_of', partner_id)]",
    )
    subscription_id = fields.Many2one(
        "sale.order",
        string="Suscripción / Contrato recurrente",
        index=True,
        tracking=True,
        domain="[('is_subscription', '=', True), ('partner_id', 'child_of', partner_id)]",
        help="Reutiliza sale.subscription (pedido con is_subscription). "
        "No genera facturación paralela.",
    )
    helpdesk_team_id = fields.Many2one(
        "helpdesk.team",
        string="Equipo Helpdesk",
        tracking=True,
    )
    sla_id = fields.Many2one(
        "helpdesk.sla",
        string="Política SLA Helpdesk",
        help="Reutiliza la política estándar de Helpdesk cuando exista.",
    )
    service_level = fields.Selection(
        selection=[
            ("basic", "Básico"),
            ("standard", "Estándar"),
            ("premium", "Premium"),
            ("custom", "Personalizado"),
        ],
        string="Nivel de servicio",
        default="standard",
        tracking=True,
    )
    sla_response_critical = fields.Char(
        string="Respuesta crítica (objetivo)",
        help="Ej.: 1 hora",
    )
    sla_response_high = fields.Char(string="Respuesta alta (objetivo)")
    sla_response_normal = fields.Char(string="Respuesta normal (objetivo)")
    coverage_schedule = fields.Char(
        string="Horario de cobertura",
        help="Ej.: Lun–Vie 8:00–18:00",
    )
    state = fields.Selection(
        selection=[
            ("prospect", "Prospecto"),
            ("evaluation", "Evaluación"),
            ("proposal", "Propuesta"),
            ("negotiation", "Negociación"),
            ("approved", "Aprobado"),
            ("implementation", "Implementación"),
            ("active", "Activo"),
            ("suspended", "Suspendido"),
            ("renewal", "En renovación"),
            ("closed", "Finalizado"),
            ("cancel", "Cancelado"),
        ],
        string="Estado",
        default="prospect",
        required=True,
        tracking=True,
        index=True,
    )
    date_start = fields.Date(string="Fecha de inicio", tracking=True)
    date_end = fields.Date(string="Fecha de finalización", tracking=True)
    date_renewal = fields.Date(string="Fecha de renovación", tracking=True)
    auto_renewal = fields.Boolean(string="Renovación automática", default=False)
    renewal_notice_days = fields.Integer(
        string="Aviso previo de renovación (días)",
        default=30,
    )
    contractual_status = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("pending_signature", "Pendiente de firma"),
            ("signed", "Firmado"),
            ("expired", "Vencido"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado contractual",
        default="draft",
        tracking=True,
    )
    # Alcance
    level_l1 = fields.Boolean(string="Nivel 1 (L1)", default=True)
    level_l2 = fields.Boolean(string="Nivel 2 (L2)", default=True)
    level_l3 = fields.Boolean(string="Nivel 3 (L3)", default=False)
    support_remote = fields.Boolean(string="Soporte remoto", default=True)
    support_onsite = fields.Boolean(string="Soporte presencial", default=False)
    included_services = fields.Html(string="Servicios incluidos")
    excluded_services = fields.Html(string="Servicios excluidos")
    scope_notes = fields.Html(string="Observaciones de alcance")
    users_covered = fields.Integer(string="Usuarios cubiertos", default=0)
    assets_covered = fields.Integer(string="Equipos / activos cubiertos", default=0)
    hours_included = fields.Float(string="Horas incluidas", default=0.0)
    visits_included = fields.Integer(string="Visitas incluidas", default=0)
    # Fee y facturación (registro; no motor paralelo)
    fee_modality = fields.Selection(
        selection=[
            ("fixed_monthly", "Fee fijo mensual"),
            ("per_user", "Fee por usuario"),
            ("hour_bag", "Bolsa de horas"),
            ("hybrid", "Servicio híbrido"),
            ("other", "Otro"),
        ],
        string="Modalidad de fee",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    fee_amount = fields.Monetary(
        string="Monto del fee",
        currency_field="currency_id",
        tracking=True,
    )
    fee_period = fields.Selection(
        selection=[
            ("monthly", "Mensual"),
            ("quarterly", "Trimestral"),
            ("semiannual", "Semestral"),
            ("annual", "Anual"),
        ],
        string="Periodicidad",
        default="monthly",
        tracking=True,
    )
    billing_day = fields.Integer(
        string="Día preferido de facturación",
        default=1,
        help="Día del mes preferido (1–28).",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto de servicio",
        domain="[('sale_ok', '=', True), ('type', '=', 'service')]",
    )
    tax_ids = fields.Many2many(
        "account.tax",
        string="Impuestos",
        domain="[('type_tax_use', '=', 'sale')]",
    )
    next_invoice_date = fields.Date(string="Próxima facturación")
    auto_billing = fields.Boolean(
        string="Facturación automática activa",
        default=False,
        help="Solo registro de intención. No activa cron propio en esta fase.",
    )
    billing_notes = fields.Text(string="Observaciones de facturación")
    internal_notes = fields.Html(string="Notas internas")
    active = fields.Boolean(default=True)

    # Contadores
    assessment_count = fields.Integer(compute="_compute_counts")
    sale_order_count = fields.Integer(compute="_compute_counts")
    ticket_count = fields.Integer(compute="_compute_counts")
    ticket_open_count = fields.Integer(compute="_compute_counts")
    ticket_closed_count = fields.Integer(compute="_compute_counts")
    invoice_count = fields.Integer(compute="_compute_counts")
    document_count = fields.Integer(compute="_compute_counts")

    @api.depends(
        "partner_id",
        "assessment_id",
        "sale_order_id",
        "subscription_id",
    )
    def _compute_counts(self):
        """Contadores para smart buttons (sudo solo para conteos; ACLs en acciones)."""
        Assessment = self.env["justech.managed.service.assessment"]
        Ticket = self.env["helpdesk.ticket"].sudo()
        Order = self.env["sale.order"].sudo()
        Move = self.env["account.move"].sudo()
        for rec in self:
            if Assessment.has_access("read"):
                assessments = Assessment.search(
                    [
                        "|",
                        ("managed_service_id", "=", rec.id),
                        ("id", "=", rec.assessment_id.id),
                    ]
                )
                rec.assessment_count = len(assessments)
            else:
                rec.assessment_count = 0
            orders = Order.search(
                [
                    "|",
                    ("justech_managed_service_id", "=", rec.id),
                    ("id", "in", [rec.sale_order_id.id, rec.subscription_id.id]),
                ]
            )
            rec.sale_order_count = len(orders)
            tickets = Ticket.search([("justech_managed_service_id", "=", rec.id)])
            rec.ticket_count = len(tickets)
            closed = tickets.filtered(lambda t: t.stage_id.fold)
            rec.ticket_closed_count = len(closed)
            rec.ticket_open_count = rec.ticket_count - rec.ticket_closed_count
            if orders:
                rec.invoice_count = Move.search_count(
                    [
                        ("move_type", "in", ("out_invoice", "out_refund")),
                        (
                            "invoice_line_ids.sale_line_ids.order_id",
                            "in",
                            orders.ids,
                        ),
                    ]
                )
            else:
                rec.invoice_count = 0
            if "documents.document" in self.env and rec.id:
                rec.document_count = (
                    self.env["documents.document"]
                    .sudo()
                    .search_count(
                        [
                            ("res_model", "=", self._name),
                            ("res_id", "=", rec.id),
                        ]
                    )
                )
            else:
                rec.document_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("Nuevo")) == _("Nuevo"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("justech.managed.service")
                    or _("Nuevo")
                )
            if not vals.get("title") and vals.get("partner_id"):
                partner = self.env["res.partner"].browse(vals["partner_id"])
                vals["title"] = _(
                    "Servicios Administrados — %(partner)s",
                    partner=partner.commercial_company_name or partner.name,
                )
        records = super().create(vals_list)
        for rec in records:
            if rec.assessment_id and not rec.assessment_id.managed_service_id:
                rec.assessment_id.managed_service_id = rec.id
            if rec.sale_order_id and not rec.sale_order_id.justech_managed_service_id:
                rec.sale_order_id.justech_managed_service_id = rec.id
            if rec.opportunity_id and not rec.opportunity_id.justech_managed_service_id:
                rec.opportunity_id.justech_managed_service_id = rec.id
        return records

    def action_set_implementation(self):
        self.write({"state": "implementation"})
        return True

    def action_set_active(self):
        today = fields.Date.context_today(self)
        for rec in self:
            vals = {"state": "active", "contractual_status": "signed"}
            if not rec.date_start:
                vals["date_start"] = today
            if not rec.date_renewal and rec.fee_period:
                delta = {
                    "monthly": relativedelta(months=1),
                    "quarterly": relativedelta(months=3),
                    "semiannual": relativedelta(months=6),
                    "annual": relativedelta(years=1),
                }.get(rec.fee_period, relativedelta(months=12))
                vals["date_renewal"] = (rec.date_start or today) + delta
            rec.write(vals)
        return True

    def action_set_suspended(self):
        self.write({"state": "suspended"})
        return True

    def action_set_closed(self):
        self.write({"state": "closed", "date_end": fields.Date.context_today(self)})
        return True

    def action_open_partner(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_assessments(self):
        self.ensure_one()
        domain = [
            "|",
            ("managed_service_id", "=", self.id),
            ("id", "=", self.assessment_id.id),
        ]
        return {
            "type": "ir.actions.act_window",
            "name": _("Levantamientos"),
            "res_model": "justech.managed.service.assessment",
            "view_mode": "list,form",
            "domain": domain,
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_managed_service_id": self.id,
                "default_consultant_id": self.technician_id.id or self.salesperson_id.id,
            },
        }

    def action_view_opportunity(self):
        self.ensure_one()
        if not self.opportunity_id:
            raise UserError(_("No hay oportunidad vinculada."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "res_id": self.opportunity_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_sale_orders(self):
        self.ensure_one()
        orders = self.env["sale.order"].search(
            [
                "|",
                ("justech_managed_service_id", "=", self.id),
                ("id", "in", [self.sale_order_id.id, self.subscription_id.id]),
            ]
        )
        action = {
            "type": "ir.actions.act_window",
            "name": _("Cotizaciones / Pedidos"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("id", "in", orders.ids)],
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_justech_managed_service_id": self.id,
                "default_opportunity_id": self.opportunity_id.id,
            },
        }
        if len(orders) == 1:
            action.update({"view_mode": "form", "res_id": orders.id})
        return action

    def action_view_subscription(self):
        self.ensure_one()
        if not self.subscription_id:
            raise UserError(
                _(
                    "No hay suscripción vinculada. Cree o asocie un pedido "
                    "con is_subscription en Sales → Subscriptions."
                )
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.subscription_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tickets"),
            "res_model": "helpdesk.ticket",
            "view_mode": "list,form",
            "domain": [("justech_managed_service_id", "=", self.id)],
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_justech_managed_service_id": self.id,
                "default_team_id": self.helpdesk_team_id.id,
            },
        }

    def action_create_ticket(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Nuevo ticket"),
            "res_model": "helpdesk.ticket",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_justech_managed_service_id": self.id,
                "default_team_id": self.helpdesk_team_id.id,
                "default_name": _("Soporte — %s", self.title or self.name),
            },
        }

    def action_view_invoices(self):
        self.ensure_one()
        orders = self.env["sale.order"].search(
            [
                "|",
                ("justech_managed_service_id", "=", self.id),
                ("id", "in", [self.sale_order_id.id, self.subscription_id.id]),
            ]
        )
        moves = self.env["account.move"].search(
            [
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("invoice_line_ids.sale_line_ids.order_id", "in", orders.ids),
            ]
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Facturas"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", moves.ids)],
        }

    def action_open_create_subscription(self):
        """Abre un pedido de suscripción estándar (sin confirmar ni facturar)."""
        self.ensure_one()
        plan = self.env["sale.subscription.plan"].search([], limit=1)
        ctx = {
            "default_partner_id": self.partner_id.id,
            "default_is_subscription": True,
            "default_justech_managed_service_id": self.id,
            "default_opportunity_id": self.opportunity_id.id,
        }
        if plan:
            ctx["default_plan_id"] = plan.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Nueva suscripción"),
            "res_model": "sale.order",
            "view_mode": "form",
            "target": "current",
            "context": ctx,
        }
