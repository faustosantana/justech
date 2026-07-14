# -*- coding: utf-8 -*-
import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class JustechRecurringFee(models.Model):
    _name = "justech.recurring.fee"
    _description = "Fee recurrente"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "next_generation_date asc, id desc"

    name = fields.Char(string="Nombre del fee", required=True, tracking=True)
    code = fields.Char(
        string="Referencia",
        copy=False,
        readonly=True,
        default=lambda self: _("Nuevo"),
        tracking=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        index=True,
        tracking=True,
        domain="[('company_id', 'in', (False, company_id))]",
    )
    partner_invoice_id = fields.Many2one(
        "res.partner",
        string="Contacto de facturación",
        domain="['|', ('id', '=', partner_id), ('parent_id', '=', partner_id)]",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Vendedor / Responsable",
        default=lambda self: self.env.user,
        tracking=True,
    )
    team_id = fields.Many2one("crm.team", string="Equipo de ventas")
    pricelist_id = fields.Many2one("product.pricelist", string="Lista de precios")
    payment_term_id = fields.Many2one("account.payment.term", string="Condiciones de pago")
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    fiscal_document_type_hint = fields.Char(
        string="Tipo de comprobante esperado",
        help="Referencia operativa (B01, B02…). El NCF lo asigna el Motor Fiscal Justech al publicar.",
    )

    line_ids = fields.One2many("justech.recurring.fee.line", "fee_id", string="Servicios")
    amount_untaxed = fields.Monetary(
        string="Base", compute="_compute_amounts", store=True, currency_field="currency_id"
    )
    amount_total = fields.Monetary(
        string="Monto", compute="_compute_amounts", store=True, currency_field="currency_id"
    )

    periodicity = fields.Selection(
        [
            ("monthly", "Mensual"),
            ("bimonthly", "Bimestral"),
            ("quarterly", "Trimestral"),
            ("semiannual", "Semestral"),
            ("annual", "Anual"),
            ("custom", "Personalizada"),
        ],
        string="Periodicidad",
        required=True,
        default="monthly",
        tracking=True,
    )
    custom_period_value = fields.Integer(string="Intervalo personalizado", default=1)
    custom_period_unit = fields.Selection(
        [("day", "Días"), ("week", "Semanas"), ("month", "Meses"), ("year", "Años")],
        string="Unidad personalizada",
        default="month",
    )
    plan_id = fields.Many2one(
        "sale.subscription.plan",
        string="Plan Odoo (opcional)",
        help="Si se indica, alinea la periodicidad con un plan de Suscripciones ya definido.",
    )

    date_start = fields.Date(
        string="Fecha de inicio",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_end = fields.Date(string="Fecha final", tracking=True)
    next_generation_date = fields.Date(
        string="Próxima generación",
        required=True,
        default=fields.Date.context_today,
        index=True,
        tracking=True,
    )
    auto_renew = fields.Boolean(string="Renovación automática", default=True, tracking=True)

    generate_document = fields.Selection(
        [
            ("quotation_draft", "Cotización en borrador"),
            ("invoice_draft", "Factura en borrador"),
            ("invoice_auto", "Factura publicada automáticamente"),
        ],
        string="Documento a generar",
        default="quotation_draft",
        required=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("active", "Activo"),
            ("paused", "Pausado"),
            ("done", "Finalizado"),
            ("cancel", "Cancelado"),
            ("attention", "Requiere atención"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    note = fields.Html(string="Notas")
    last_error = fields.Text(string="Error actual", copy=False, readonly=True)
    last_run_at = fields.Datetime(string="Última ejecución", copy=False, readonly=True)
    last_document_name = fields.Char(string="Último documento", compute="_compute_document_stats")
    cycle_count = fields.Integer(string="Ciclos", compute="_compute_document_stats")
    next_step = fields.Char(string="Próximo paso", compute="_compute_next_step")
    due_within_7_days = fields.Boolean(
        string="Próximos 7 días",
        compute="_compute_due_within_7_days",
        search="_search_due_within_7_days",
    )

    cycle_ids = fields.One2many("justech.recurring.fee.cycle", "fee_id", string="Ciclos")
    sale_order_ids = fields.One2many("sale.order", "justech_fee_id", string="Cotizaciones / Pedidos")
    invoice_ids = fields.One2many("account.move", "justech_fee_id", string="Facturas")
    sale_order_count = fields.Integer(compute="_compute_document_stats")
    invoice_count = fields.Integer(compute="_compute_document_stats")

    @api.depends("line_ids.price_subtotal", "line_ids.price_total")
    def _compute_amounts(self):
        for fee in self:
            fee.amount_untaxed = sum(fee.line_ids.mapped("price_subtotal"))
            fee.amount_total = sum(fee.line_ids.mapped("price_total"))

    @api.depends("cycle_ids", "sale_order_ids", "invoice_ids")
    def _compute_document_stats(self):
        for fee in self:
            fee.cycle_count = len(fee.cycle_ids)
            fee.sale_order_count = len(fee.sale_order_ids)
            fee.invoice_count = len(fee.invoice_ids)
            last = fee.cycle_ids[:1]
            fee.last_document_name = last.document_name if last else False

    @api.depends("state", "next_generation_date", "generate_document", "last_error")
    def _compute_next_step(self):
        labels = {
            "quotation_draft": _("Revisar cotización generada"),
            "invoice_draft": _("Revisar y publicar factura"),
            "invoice_auto": _("Verificar factura publicada"),
        }
        for fee in self:
            if fee.last_error or fee.state == "attention":
                fee.next_step = _("Resolver error / atención requerida")
            elif fee.state == "paused":
                fee.next_step = _("Reactivar fee")
            elif fee.state == "active":
                fee.next_step = _(
                    "Esperar generación (%(date)s) → %(doc)s"
                ) % {
                    "date": fee.next_generation_date or "-",
                    "doc": labels.get(fee.generate_document, ""),
                }
            elif fee.state == "draft":
                fee.next_step = _("Activar fee")
            else:
                fee.next_step = False

    @api.depends("next_generation_date")
    def _compute_due_within_7_days(self):
        today = fields.Date.context_today(self)
        limit = today + relativedelta(days=7)
        for fee in self:
            fee.due_within_7_days = bool(
                fee.next_generation_date and today <= fee.next_generation_date <= limit
            )

    def _search_due_within_7_days(self, operator, value):
        today = fields.Date.context_today(self)
        limit = today + relativedelta(days=7)
        if (operator == "=" and value) or (operator == "!=" and not value):
            return [
                ("next_generation_date", ">=", today),
                ("next_generation_date", "<=", limit),
            ]
        return [
            "|",
            ("next_generation_date", "<", today),
            ("next_generation_date", ">", limit),
        ]

    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        if not self.plan_id:
            return
        unit = self.plan_id.billing_period_unit
        value = self.plan_id.billing_period_value or 1
        mapping = {
            ("month", 1): "monthly",
            ("month", 2): "bimonthly",
            ("month", 3): "quarterly",
            ("month", 6): "semiannual",
            ("year", 1): "annual",
        }
        self.periodicity = mapping.get((unit, value), "custom")
        if self.periodicity == "custom":
            self.custom_period_value = value
            self.custom_period_unit = {
                "week": "week",
                "month": "month",
                "year": "year",
            }.get(unit, "month")

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and not self.partner_invoice_id:
            self.partner_invoice_id = self.partner_id.address_get(["invoice"]).get("invoice")

    @api.constrains("generate_document")
    def _check_invoice_auto_permission(self):
        for fee in self:
            if fee.generate_document != "invoice_auto":
                continue
            if not self.env.user.has_group("base.group_system"):
                raise AccessError(
                    _(
                        "Solo administradores autorizados pueden configurar "
                        "«Factura publicada automáticamente». Riesgo fiscal."
                    )
                )

    @api.constrains("date_start", "date_end", "next_generation_date", "custom_period_value")
    def _check_dates(self):
        for fee in self:
            if fee.date_end and fee.date_start and fee.date_end < fee.date_start:
                raise ValidationError(_("La fecha final no puede ser anterior al inicio."))
            if fee.periodicity == "custom" and fee.custom_period_value <= 0:
                raise ValidationError(_("El intervalo personalizado debe ser mayor que cero."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", _("Nuevo")) == _("Nuevo"):
                vals["code"] = self.env["ir.sequence"].next_by_code("justech.recurring.fee") or _("Nuevo")
            if vals.get("generate_document") == "invoice_auto" and not self.env.user.has_group(
                "base.group_system"
            ):
                raise AccessError(
                    _("Solo administradores pueden crear fees con factura automática.")
                )
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("generate_document") == "invoice_auto" and not self.env.user.has_group(
            "base.group_system"
        ):
            raise AccessError(
                _("Solo administradores pueden activar factura automática en un fee.")
            )
        tracked_line_fields = {"product_id", "product_uom_qty", "price_unit", "tax_ids"}
        # Auditoría de cambios de cabecera relevantes para ciclos futuros
        price_keys = {"periodicity", "custom_period_value", "custom_period_unit", "currency_id"}
        res = super().write(vals)
        touch = set(vals) & price_keys
        if touch:
            for fee in self:
                fee.message_post(
                    body=_(
                        "Cambio de configuración del fee (aplica a ciclos futuros): %(fields)s"
                    )
                    % {"fields": ", ".join(sorted(touch))}
                )
        return res

    def action_activate(self):
        for fee in self:
            if not fee.line_ids:
                raise UserError(_("Agregue al menos un servicio/producto al fee."))
            fee.write({"state": "active", "last_error": False})
        return True

    def action_pause(self):
        self.write({"state": "paused"})
        return True

    def action_reactivate(self):
        """Abrir asistente: conservar próxima fecha o reprogramar."""
        self.ensure_one()
        if self.date_end and self.date_end < fields.Date.context_today(self):
            raise UserError(_("El fee tiene fecha final vencida; ajuste la fecha final."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reactivar fee"),
            "res_model": "justech.recurring.fee.reactivate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_fee_id": self.id,
                "default_keep_next_date": True,
                "default_next_generation_date": self.next_generation_date,
            },
        }

    def action_done(self):
        self.write({"state": "done"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        self.write({"state": "draft", "last_error": False})
        return True

    def _period_delta(self):
        self.ensure_one()
        mapping = {
            "monthly": relativedelta(months=1),
            "bimonthly": relativedelta(months=2),
            "quarterly": relativedelta(months=3),
            "semiannual": relativedelta(months=6),
            "annual": relativedelta(years=1),
        }
        if self.periodicity in mapping:
            return mapping[self.periodicity]
        value = self.custom_period_value or 1
        unit = self.custom_period_unit or "month"
        if unit == "day":
            return relativedelta(days=value)
        if unit == "week":
            return relativedelta(weeks=value)
        if unit == "year":
            return relativedelta(years=value)
        return relativedelta(months=value)

    def _compute_period_bounds(self, scheduled_date):
        self.ensure_one()
        period_from = scheduled_date
        period_to = scheduled_date + self._period_delta() - relativedelta(days=1)
        return period_from, period_to

    def _period_key(self, period_from, period_to, doc_type):
        return f"{period_from.isoformat()}|{period_to.isoformat()}|{doc_type}"

    def _taxes_for_company(self, taxes):
        """Solo impuestos de la empresa del fee (o sin empresa) — multiempresa seguro."""
        self.ensure_one()
        company = self.company_id
        return taxes.filtered(
            lambda t: not t.company_id or t.company_id == company
        )

    def _prepare_order_lines(self):
        self.ensure_one()
        commands = []
        for line in self.line_ids:
            tax_ids = self._taxes_for_company(line.tax_ids)
            commands.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "name": line.name or line.product_id.display_name,
                        "product_uom_qty": line.product_uom_qty,
                        "price_unit": line.price_unit,
                        "tax_ids": [(6, 0, tax_ids.ids)],
                        "product_uom_id": line.product_uom_id.id,
                        "justech_fee_line_id": line.id,
                    },
                )
            )
        return commands

    def _prepare_invoice_lines(self):
        self.ensure_one()
        commands = []
        for line in self.line_ids:
            tax_ids = self._taxes_for_company(line.tax_ids)
            commands.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "name": line.name or line.product_id.display_name,
                        "quantity": line.product_uom_qty,
                        "price_unit": line.price_unit,
                        "tax_ids": [(6, 0, tax_ids.ids)],
                        "product_uom_id": line.product_uom_id.id,
                    },
                )
            )
        return commands

    def _find_existing_cycle(self, period_key):
        self.ensure_one()
        return self.env["justech.recurring.fee.cycle"].sudo().search(
            [("fee_id", "=", self.id), ("period_key", "=", period_key)], limit=1
        )

    def action_generate_now(self):
        """Generación manual / forzada del ciclo pendiente (misma lógica del cron)."""
        for fee in self:
            fee._generate_one_cycle(force=True)
        return True

    def _generate_one_cycle(self, force=False):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.state != "active" and not force:
            return False
        if self.state in ("cancel", "done"):
            return False
        if not force and self.next_generation_date and self.next_generation_date > today:
            return False
        if self.date_end and self.next_generation_date and self.next_generation_date > self.date_end:
            self.write({"state": "done", "last_error": False})
            return False
        if not self.line_ids:
            self.write(
                {
                    "state": "attention",
                    "last_error": _("Sin líneas de servicio; no se puede generar el ciclo."),
                }
            )
            return False

        scheduled = self.next_generation_date or today
        period_from, period_to = self._compute_period_bounds(scheduled)
        doc_type = self.generate_document
        period_key = self._period_key(period_from, period_to, doc_type)
        existing = self._find_existing_cycle(period_key)
        if existing:
            self.message_post(
                body=_(
                    "Ciclo ya existente para %(period)s (%(doc)s). Idempotencia: no se duplicó."
                )
                % {"period": period_key, "doc": existing.document_name or existing.id}
            )
            # Avanzar fecha si quedó atrasada
            self._advance_next_date(scheduled)
            return existing

        cycle_number = len(self.cycle_ids) + 1
        try:
            # Savepoint: si falla la creación, no quedan cotizaciones/facturas huérfanas.
            with self.env.cr.savepoint():
                document = self._create_cycle_document(period_from, period_to, cycle_number)
                cycle = self.env["justech.recurring.fee.cycle"].sudo().create(
                    {
                        "fee_id": self.id,
                        "company_id": self.company_id.id,
                        "period_key": period_key,
                        "period_from": period_from,
                        "period_to": period_to,
                        "cycle_number": cycle_number,
                        "scheduled_date": scheduled,
                        "generated_at": fields.Datetime.now(),
                        "document_type": doc_type,
                        "sale_order_id": document._name == "sale.order" and document.id or False,
                        "invoice_id": document._name == "account.move" and document.id or False,
                        "document_name": document.display_name,
                        "state": "done",
                    }
                )
            self.write(
                {
                    "last_run_at": fields.Datetime.now(),
                    "last_error": False,
                    "state": "active" if self.state == "attention" else self.state,
                }
            )
            self._advance_next_date(scheduled)
            try:
                self._notify_responsible(document, cycle)
            except Exception as notify_exc:  # noqa: BLE001
                _logger.warning(
                    "Fee %s: documento generado pero falló la notificación: %s",
                    self.code,
                    notify_exc,
                )
                self.message_post(
                    body=_("Documento generado; notificación falló: %s") % notify_exc
                )
            return cycle
        except Exception as exc:  # noqa: BLE001 — registrar para cron actionable
            err = str(exc)
            _logger.exception("Fee %s: error generando ciclo", self.code)
            self.sudo().write(
                {
                    "state": "attention",
                    "last_error": err,
                    "last_run_at": fields.Datetime.now(),
                }
            )
            self.message_post(body=_("Error al generar ciclo: %s") % err)
            return False

    def _advance_next_date(self, scheduled):
        self.ensure_one()
        nxt = scheduled + self._period_delta()
        vals = {"next_generation_date": nxt}
        if self.date_end and nxt > self.date_end:
            vals["state"] = "done"
        self.write(vals)

    def _create_cycle_document(self, period_from, period_to, cycle_number):
        self.ensure_one()
        period_label = _(
            "Período: %(start)s al %(end)s\nFee origen: %(fee)s\nCiclo: %(cycle)s"
        ) % {
            "start": period_from.strftime("%d/%m/%Y"),
            "end": period_to.strftime("%d/%m/%Y"),
            "fee": self.code,
            "cycle": cycle_number,
        }
        mode = self.generate_document
        if mode == "quotation_draft":
            order = (
                self.env["sale.order"]
                .with_company(self.company_id)
                .sudo()
                .create(
                    {
                        "partner_id": self.partner_id.id,
                        "partner_invoice_id": (self.partner_invoice_id or self.partner_id).id,
                        "company_id": self.company_id.id,
                        "user_id": self.user_id.id,
                        "team_id": self.team_id.id if self.team_id else False,
                        "pricelist_id": self.pricelist_id.id if self.pricelist_id else False,
                        "payment_term_id": self.payment_term_id.id
                        if self.payment_term_id
                        else False,
                        "currency_id": self.currency_id.id,
                        "origin": self.code,
                        "client_order_ref": self.code,
                        "note": period_label,
                        "justech_fee_id": self.id,
                        "justech_fee_period_from": period_from,
                        "justech_fee_period_to": period_to,
                        "justech_fee_cycle_number": cycle_number,
                        "order_line": self._prepare_order_lines(),
                    }
                )
            )
            return order

        # Factura (borrador o auto-publicada)
        move = (
            self.env["account.move"]
            .with_company(self.company_id)
            .sudo()
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": (self.partner_invoice_id or self.partner_id).id,
                    "company_id": self.company_id.id,
                    "invoice_user_id": self.user_id.id,
                    "invoice_payment_term_id": self.payment_term_id.id
                    if self.payment_term_id
                    else False,
                    "currency_id": self.currency_id.id,
                    "invoice_origin": self.code,
                    "narration": period_label,
                    "justech_fee_id": self.id,
                    "justech_fee_period_from": period_from,
                    "justech_fee_period_to": period_to,
                    "justech_fee_cycle_number": cycle_number,
                    "invoice_line_ids": self._prepare_invoice_lines(),
                }
            )
        )
        if mode == "invoice_auto":
            # Motor Fiscal Justech actúa en _post; si falla, queda como attention.
            move.action_post()
        return move

    def _notify_responsible(self, document, cycle):
        self.ensure_one()
        # En DEV no se envían correos reales: solo actividad/chatter.
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=self.user_id.id or self.env.user.id,
            summary=_("Fee %(fee)s — documento %(doc)s listo")
            % {"fee": self.code, "doc": document.display_name},
            note=_("Ciclo %(n)s · %(from)s → %(to)s")
            % {
                "n": cycle.cycle_number,
                "from": cycle.period_from,
                "to": cycle.period_to,
            },
        )

    @api.model
    def _cron_generate_due_fees(self):
        """Cron: fees activos con próxima generación vencida (idempotente por ciclo)."""
        # Advisory lock: evita doble ejecución concurrente del cron.
        lock_key = 87231401
        self.env.cr.execute(
            "SELECT pg_try_advisory_lock(%s)",
            (lock_key,),
        )
        acquired = self.env.cr.fetchone()[0]
        if not acquired:
            _logger.info("justech_recurring_fee cron: lock ocupado, se omite esta corrida")
            return False
        try:
            today = fields.Date.context_today(self)
            fees = self.sudo().search(
                [
                    ("state", "=", "active"),
                    ("next_generation_date", "<=", today),
                    ("auto_renew", "=", True),
                ]
            )
            for fee in fees:
                try:
                    with self.env.cr.savepoint():
                        # Lock por fila del fee
                        self.env.cr.execute(
                            "SELECT id FROM justech_recurring_fee "
                            "WHERE id = %s FOR UPDATE NOWAIT",
                            (fee.id,),
                        )
                        fee._generate_one_cycle(force=False)
                except Exception as exc:  # noqa: BLE001
                    _logger.exception("Fee cron error id=%s", fee.id)
                    fee.sudo().write(
                        {
                            "state": "attention",
                            "last_error": str(exc),
                            "last_run_at": fields.Datetime.now(),
                        }
                    )
            return True
        finally:
            self.env.cr.execute("SELECT pg_advisory_unlock(%s)", (lock_key,))

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cotizaciones / Pedidos"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("justech_fee_id", "=", self.id)],
            "context": {"default_justech_fee_id": self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Facturas"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("justech_fee_id", "=", self.id)],
            "context": {
                "default_justech_fee_id": self.id,
                "default_move_type": "out_invoice",
            },
        }
