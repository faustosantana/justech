from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class JustechDoNcfRange(models.Model):
    _name = "justech.do.ncf.range"
    _description = "Dominican NCF Authorized Range"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_to, prefix"

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    document_type_id = fields.Many2one(
        "justech.do.fiscal.document.type",
        required=True,
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    prefix = fields.Char(related="document_type_id.prefix", store=True)
    flow_kind = fields.Selection(
        selection=[
            ("sales", "Ventas"),
            ("purchase_issued", "Compras Emitidos"),
        ],
        string="Flujo",
        compute="_compute_flow_kind",
        store=True,
    )
    journal_ids = fields.Many2many(
        "account.journal",
        string="Diarios",
        domain="[('company_id', '=', company_id)]",
    )
    authorization_number = fields.Char(string="Autorización DGII", tracking=True)
    sequence_start = fields.Integer(
        string="Secuencia inicial", required=True, default=1, tracking=True
    )
    sequence_end = fields.Integer(
        string="Secuencia final", required=True, tracking=True
    )
    next_sequence = fields.Integer(
        string="Próxima secuencia", required=True, default=1, tracking=True
    )
    date_from = fields.Date(
        string="Vigente desde",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_to = fields.Date(string="Fecha de vencimiento", required=True, tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("active", "Activo"),
            ("depleted", "Agotado"),
            ("expired", "Vencido"),
            ("cancelled", "Cerrado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    remaining_count = fields.Integer(
        string="Disponibles", compute="_compute_metrics"
    )
    consumed_count = fields.Integer(
        string="Consumidos", compute="_compute_metrics"
    )
    authorized_total = fields.Integer(
        string="Total autorizado", compute="_compute_metrics"
    )
    pct_used = fields.Float(string="% Consumido", compute="_compute_metrics")
    next_ncf_display = fields.Char(
        string="Próximo NCF", compute="_compute_next_ncf_display"
    )
    consumption_ids = fields.One2many(
        "justech.do.ncf.consumption",
        "range_id",
        string="Consumo",
    )
    # Umbrales opcionales por rango (0 = heredar de compañía)
    alert_threshold_preventive = fields.Integer(
        string="Umbral preventivo (disponibles)",
        default=0,
        help="0 = usar umbral de la compañía.",
    )
    alert_threshold_critical = fields.Integer(
        string="Umbral crítico (disponibles)",
        default=0,
        help="0 = usar umbral de la compañía.",
    )
    # Idempotencia de alertas (ciclo = sequence_end + date_to)
    alert_preventive_cycle = fields.Char(copy=False)
    alert_critical_cycle = fields.Char(copy=False)
    alert_depleted_cycle = fields.Char(copy=False)
    alert_expiring_cycle = fields.Char(copy=False)
    alert_expired_cycle = fields.Char(copy=False)

    STANDARD_RANGE_NAMES = {
        "B01": "B01 Factura de Crédito Fiscal",
        "B02": "B02 Factura de Consumo",
        "B03": "B03 Nota de Débito",
        "B04": "B04 Nota de Crédito",
        "B11": "B11 — Comprobante de Compras / Proveedor Informal",
        "B13": "B13 — Comprobante para Gastos Menores",
        "B14": "B14 — Regímenes Especiales de Tributación",
        "B15": "B15 — Comprobante Gubernamental",
        "B17": "B17 — Comprobante para Pagos al Exterior",
    }
    PURCHASE_ISSUED_PREFIXES = frozenset({"B11", "B13", "B17"})

    _sql_constraints = [
        (
            "sequence_check",
            "CHECK(sequence_start > 0 AND sequence_end >= sequence_start)",
            "Invalid sequence bounds.",
        ),
    ]

    @api.depends("prefix")
    def _compute_flow_kind(self):
        for rec in self:
            if rec.prefix in self.PURCHASE_ISSUED_PREFIXES:
                rec.flow_kind = "purchase_issued"
            else:
                rec.flow_kind = "sales"

    # ------------------------------------------------------------------
    # Fórmula única (FASE 3)
    # ------------------------------------------------------------------
    def _metrics(self):
        """Return authorized, consumed, available, pct for this range only."""
        self.ensure_one()
        authorized = max(int(self.sequence_end) - int(self.sequence_start) + 1, 0)
        consumed = max(int(self.next_sequence) - int(self.sequence_start), 0)
        available = max(int(self.sequence_end) - int(self.next_sequence) + 1, 0)
        if authorized <= 0:
            pct = 0.0
        else:
            pct = min(100.0, max(0.0, round(100.0 * consumed / authorized, 2)))
        return authorized, consumed, available, pct

    @api.depends("sequence_start", "sequence_end", "next_sequence")
    def _compute_metrics(self):
        for rec in self:
            authorized, consumed, available, pct = rec._metrics()
            rec.authorized_total = authorized
            rec.consumed_count = consumed
            rec.remaining_count = available
            rec.pct_used = pct

    @api.depends("prefix", "next_sequence")
    def _compute_next_ncf_display(self):
        for rec in self:
            if rec.prefix and rec.next_sequence:
                rec.next_ncf_display = f"{rec.prefix}{int(rec.next_sequence):08d}"
            else:
                rec.next_ncf_display = False

    def _alert_cycle_key(self):
        self.ensure_one()
        return f"{self.sequence_end}|{self.date_to}|{self.sequence_start}"

    def _threshold_preventive(self):
        self.ensure_one()
        if self.alert_threshold_preventive > 0:
            return self.alert_threshold_preventive
        return self.company_id.justech_do_ncf_alert_threshold_preventive or 20

    def _threshold_critical(self):
        self.ensure_one()
        if self.alert_threshold_critical > 0:
            return self.alert_threshold_critical
        return self.company_id.justech_do_ncf_alert_threshold_critical or 5

    def _expiry_alert_days(self):
        self.ensure_one()
        return (
            self.company_id.justech_do_ncf_alert_expiry_days
            or self.company_id.justech_do_ncf_alert_days
            or 15
        )

    # ------------------------------------------------------------------
    # Estado (FASE 4)
    # ------------------------------------------------------------------
    def _compute_target_state(self):
        """Priority: cancelled > expired > depleted > active > draft."""
        self.ensure_one()
        if self.state == "cancelled":
            return "cancelled"
        if self.state == "draft":
            return "draft"
        today = fields.Date.context_today(self)
        if self.date_to and today > self.date_to:
            return "expired"
        _a, _c, available, _p = self._metrics()
        if available <= 0 or self.next_sequence > self.sequence_end:
            return "depleted"
        return "active"

    def _recompute_operational_state(self):
        for rec in self:
            target = rec._compute_target_state()
            if rec.state != target:
                super(JustechDoNcfRange, rec).write({"state": target})

    @api.model
    def normalize_range_names(self):
        """Normaliza nombres de rango al estándar Justech (solo metadato name)."""
        Range = self.sudo()
        for prefix, standard_name in self.STANDARD_RANGE_NAMES.items():
            for rng in Range.search([("prefix", "=", prefix)]):
                if any(
                    token in (rng.name or "").lower()
                    for token in ("rollout", "std", "test", "dev", "piloto", "gate")
                ) or not rng.name.startswith(prefix):
                    rng.name = standard_name

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to < rec.date_from:
                raise ValidationError(_("End date must be after start date."))

    @api.constrains("sequence_start", "sequence_end", "next_sequence")
    def _check_sequence_bounds(self):
        for rec in self:
            if rec.sequence_end < rec.sequence_start:
                raise ValidationError(
                    _("La secuencia final no puede ser menor que la inicial.")
                )
            if rec.next_sequence < rec.sequence_start:
                raise ValidationError(
                    _("La próxima secuencia no puede ser menor que la inicial.")
                )

    @api.model
    def _validate_ncf_format(self, ncf):
        return self.env["justech.do.fiscal.validator.service"].validate_ncf_format(ncf)

    def action_activate(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft ranges can be activated."))
            if fields.Date.today() > rec.date_to:
                raise UserError(_("Cannot activate an already expired range."))
            rec.next_sequence = max(rec.next_sequence, rec.sequence_start)
            rec.state = "active"
            rec._recompute_operational_state()

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_set_draft(self):
        self.write({"state": "draft"})

    def write(self, vals):
        tracked = {"sequence_start", "sequence_end", "next_sequence", "date_to", "date_from"}
        expanding = {}
        for rec in self:
            if "sequence_end" in vals:
                new_end = vals["sequence_end"]
                if new_end is not None and int(new_end) > int(rec.sequence_end):
                    expanding[rec.id] = {
                        "old_end": rec.sequence_end,
                        "next": rec.next_sequence,
                        "prefix": rec.prefix,
                        "company": rec.company_id.display_name,
                    }
                if new_end is not None and int(new_end) < int(rec.next_sequence):
                    raise ValidationError(
                        _(
                            "La secuencia final (%(end)s) no puede ser menor que "
                            "la próxima secuencia (%(next)s).",
                            end=new_end,
                            next=rec.next_sequence,
                        )
                    )
        ctx_vals = set(vals.keys()) & tracked
        res = super().write(vals)
        if vals.get("state") not in ("cancelled", "draft"):
            if ctx_vals or "state" not in vals:
                self._recompute_operational_state()
        # Ampliación: reset alertas del ciclo anterior + chatter
        for rec in self:
            info = expanding.get(rec.id)
            if not info:
                continue
            super(JustechDoNcfRange, rec).write(
                {
                    "alert_preventive_cycle": False,
                    "alert_critical_cycle": False,
                    "alert_depleted_cycle": False,
                    "alert_expiring_cycle": False,
                }
            )
            _a, _c, available, pct = rec._metrics()
            rec.message_post(
                body=_(
                    "Rango %(prefix)s de %(company)s ampliado hasta %(ncf_end)s.<br/>"
                    "Próximo NCF preservado: %(next_ncf)s.<br/>"
                    "Disponibles: %(available)s.<br/>"
                    "Consumo: %(pct)s %%.<br/>"
                    "Estado: %(state)s."
                )
                % {
                    "prefix": info["prefix"] or rec.prefix,
                    "company": info["company"],
                    "ncf_end": f"{rec.prefix}{int(rec.sequence_end):08d}",
                    "next_ncf": rec.next_ncf_display or "",
                    "available": available,
                    "pct": pct,
                    "state": dict(rec._fields["state"].selection).get(rec.state, rec.state),
                }
            )
            rec._close_depleted_activities()
        return res

    def _check_usable(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        self._recompute_operational_state()
        if self.state == "cancelled":
            raise UserError(
                _(
                    "El rango %(name)s de %(company)s está cerrado.",
                    name=self.name,
                    company=self.company_id.display_name,
                )
            )
        if self.state == "expired" or (self.date_to and today > self.date_to):
            if self.state != "expired":
                self.state = "expired"
            raise UserError(
                _(
                    "El rango %(prefix)s de %(company)s está vencido. "
                    "No se pueden emitir NCF para esta empresa.",
                    prefix=self.prefix,
                    company=self.company_id.display_name,
                )
            )
        if self.state != "active":
            raise UserError(
                _(
                    "El rango %(prefix)s de %(company)s no está activo (estado: %(state)s).",
                    prefix=self.prefix,
                    company=self.company_id.display_name,
                    state=self.state,
                )
            )
        _a, _c, available, _p = self._metrics()
        if available <= 0 or self.next_sequence > self.sequence_end:
            self.state = "depleted"
            raise UserError(
                _(
                    "El rango %(prefix)s de %(company)s está agotado. "
                    "No existen NCF disponibles para esta empresa.",
                    prefix=self.prefix,
                    company=self.company_id.display_name,
                )
            )

    def consume_next(self, move):
        self.ensure_one()
        self.env.cr.execute(
            """
            SELECT next_sequence, sequence_end, state, date_to, document_type_id
            FROM justech_do_ncf_range
            WHERE id = %s
            FOR UPDATE
            """,
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row:
            raise UserError(_("NCF range %(name)s not found.", name=self.name))
        next_seq, seq_end, state, date_to, doc_type_id = row
        today = fields.Date.context_today(self)
        if state == "cancelled":
            raise UserError(
                _(
                    "El rango %(prefix)s de %(company)s está cerrado.",
                    prefix=self.prefix,
                    company=self.company_id.display_name,
                )
            )
        if state == "expired" or (date_to and today > date_to):
            self.env.cr.execute(
                "UPDATE justech_do_ncf_range SET state = 'expired' WHERE id = %s",
                [self.id],
            )
            raise UserError(
                _(
                    "El rango %(prefix)s de %(company)s está vencido. "
                    "No se pueden emitir NCF para esta empresa.",
                    prefix=self.prefix,
                    company=self.company_id.display_name,
                )
            )
        if state != "active":
            raise UserError(
                _(
                    "El rango %(prefix)s de %(company)s no está activo.",
                    prefix=self.prefix,
                    company=self.company_id.display_name,
                )
            )
        if next_seq > seq_end:
            self.env.cr.execute(
                "UPDATE justech_do_ncf_range SET state = 'depleted' WHERE id = %s",
                [self.id],
            )
            raise UserError(
                _(
                    "El rango %(prefix)s de %(company)s está agotado. "
                    "No existen NCF disponibles para esta empresa.",
                    prefix=self.prefix,
                    company=self.company_id.display_name,
                )
            )
        doc_type = self.env["justech.do.fiscal.document.type"].browse(doc_type_id)
        ncf = doc_type.format_ncf(next_seq)
        if move.company_id != self.company_id:
            raise UserError(
                _(
                    "El rango NCF pertenece a %(range_co)s pero el documento es de %(move_co)s.",
                    range_co=self.company_id.display_name,
                    move_co=move.company_id.display_name,
                )
            )
        self.env["justech.do.ncf.consumption"].sudo().with_context(
            justech_ncf_engine=True
        ).create(
            {
                "range_id": self.id,
                "move_id": move.id,
                "ncf": ncf,
                "sequence_number": next_seq,
                "state": "consumed",
            }
        )
        new_next = next_seq + 1
        new_state = "depleted" if new_next > seq_end else "active"
        self.env.cr.execute(
            """
            UPDATE justech_do_ncf_range
            SET next_sequence = %s, state = %s
            WHERE id = %s
            """,
            [new_next, new_state, self.id],
        )
        self.invalidate_recordset(["next_sequence", "state"])
        return ncf

    @api.model
    def _find_active_range(self, document_type, journal, company):
        domain = [
            ("company_id", "=", company.id),
            ("document_type_id", "=", document_type.id),
            ("state", "=", "active"),
        ]
        ranges = self.search(domain, order="date_to")
        if journal:
            specific = ranges.filtered(lambda r: journal in r.journal_ids)
            if specific:
                ranges = specific
            else:
                ranges = ranges.filtered(lambda r: not r.journal_ids)
        today = fields.Date.context_today(self)
        ranges = ranges.filtered(
            lambda r: r.date_to >= today and r.next_sequence <= r.sequence_end
        )
        return ranges[:1]

    @api.model
    def _find_active_range_for_update(self, document_type, journal, company):
        """Return one usable range with a row lock on the selected record."""
        today = fields.Date.context_today(self)
        domain = [
            ("company_id", "=", company.id),
            ("document_type_id", "=", document_type.id),
            ("state", "=", "active"),
            ("date_to", ">=", today),
        ]
        ranges = self.search(domain, order="date_to")
        ranges = ranges.filtered(lambda r: r.next_sequence <= r.sequence_end)
        if journal:
            specific = ranges.filtered(lambda r: journal in r.journal_ids)
            if specific:
                ranges = specific
            else:
                ranges = ranges.filtered(lambda r: not r.journal_ids)
        if not ranges:
            return self.browse()
        self.flush_model()
        self.env.cr.execute(
            """
            SELECT id
            FROM justech_do_ncf_range
            WHERE id = ANY(%s)
            ORDER BY date_to, id
            FOR UPDATE
            """,
            [ranges.ids],
        )
        locked_ids = [row[0] for row in self.env.cr.fetchall()]
        locked = self.browse(locked_ids)
        if journal:
            specific = locked.filtered(lambda r: journal in r.journal_ids)
            if specific:
                locked = specific
            else:
                locked = locked.filtered(lambda r: not r.journal_ids)
        return locked[:1]

    # ------------------------------------------------------------------
    # Alertas multiempresa (FASES 6–9)
    # ------------------------------------------------------------------
    def _alert_recipient_users(self):
        self.ensure_one()
        company = self.company_id
        users = self.env["res.users"]
        for xmlid in (
            "justech_l10n_do_base.group_justech_do_fiscal_manager",
            "justech_fiscal_admin.group_justech_fiscal_admin_manager",
            "base.group_system",
        ):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                # Odoo 19: user_ids (no .users)
                users |= group.user_ids
        return users.filtered(
            lambda u: u.active
            and u.share is False
            and bool(u.email)
            and company in u.company_ids
        )

    def _alert_body(self, alert_type):
        self.ensure_one()
        _a, consumed, available, pct = self._metrics()
        flow = dict(self._fields["flow_kind"].selection).get(
            self.flow_kind, self.flow_kind or ""
        )
        return _(
            "<p><b>Alerta NCF — %(alert)s</b></p>"
            "<ul>"
            "<li>Empresa: %(company)s</li>"
            "<li>Tipo: %(prefix)s — %(name)s</li>"
            "<li>Flujo: %(flow)s</li>"
            "<li>Autorización DGII: %(auth)s</li>"
            "<li>Secuencia: %(start)s – %(end)s</li>"
            "<li>Próxima secuencia: %(next)s</li>"
            "<li>Próximo NCF: %(next_ncf)s</li>"
            "<li>Disponibles: %(available)s</li>"
            "<li>Consumidos: %(consumed)s</li>"
            "<li>Porcentaje consumido: %(pct)s %%</li>"
            "<li>Vencimiento: %(date_to)s</li>"
            "<li>Estado: %(state)s</li>"
            "</ul>"
        ) % {
            "alert": alert_type,
            "company": self.company_id.display_name,
            "prefix": self.prefix or "",
            "name": self.name or "",
            "flow": flow,
            "auth": self.authorization_number or "—",
            "start": self.sequence_start,
            "end": self.sequence_end,
            "next": self.next_sequence,
            "next_ncf": self.next_ncf_display or "—",
            "available": available,
            "consumed": consumed,
            "pct": pct,
            "date_to": self.date_to or "—",
            "state": dict(self._fields["state"].selection).get(self.state, self.state),
        }

    def _close_depleted_activities(self):
        Activity = self.env["mail.activity"]
        for rec in self:
            acts = Activity.search(
                [
                    ("res_model", "=", rec._name),
                    ("res_id", "=", rec.id),
                    ("summary", "ilike", "Agotado"),
                ]
            )
            acts.action_feedback(feedback=_("Rango ampliado; alerta de agotamiento resuelta."))

    def _emit_alert(self, kind, summary, cycle_field):
        self.ensure_one()
        cycle = self._alert_cycle_key()
        if self[cycle_field] == cycle:
            return False
        users = self._alert_recipient_users()
        if not users:
            return False
        body = self._alert_body(summary)
        for user in users:
            self.activity_schedule(
                act_type_xmlid="justech_l10n_do_ncf.mail_activity_data_ncf_range_alert",
                summary=summary,
                note=body,
                user_id=user.id,
            )
        self.message_post(
            body=body,
            partner_ids=users.mapped("partner_id").ids,
            subtype_xmlid="mail.mt_comment",
            subject=summary,
        )
        self[cycle_field] = cycle
        return True

    def _process_alerts(self):
        """Evaluate and emit alerts for this range (company-scoped)."""
        self.ensure_one()
        if self.state == "draft":
            return
        today = fields.Date.context_today(self)
        _a, _c, available, _p = self._metrics()
        # Ensure state is current before alerting
        if self.state != "cancelled":
            target = self._compute_target_state()
            if self.state != target:
                self.state = target

        if self.state == "expired" or (self.date_to and today > self.date_to):
            self._emit_alert(
                "expired",
                _("NCF vencido — %(company)s / %(prefix)s")
                % {"company": self.company_id.name, "prefix": self.prefix},
                "alert_expired_cycle",
            )
            return

        if self.state == "cancelled":
            return

        if available <= 0 or self.state == "depleted":
            self._emit_alert(
                "depleted",
                _("NCF agotado — %(company)s / %(prefix)s")
                % {"company": self.company_id.name, "prefix": self.prefix},
                "alert_depleted_cycle",
            )
            return

        critical = self._threshold_critical()
        preventive = self._threshold_preventive()
        if available <= critical:
            self._emit_alert(
                "critical",
                _("NCF crítico (%(n)s disp.) — %(company)s / %(prefix)s")
                % {
                    "n": available,
                    "company": self.company_id.name,
                    "prefix": self.prefix,
                },
                "alert_critical_cycle",
            )
        elif available <= preventive:
            self._emit_alert(
                "preventive",
                _("NCF preventivo (%(n)s disp.) — %(company)s / %(prefix)s")
                % {
                    "n": available,
                    "company": self.company_id.name,
                    "prefix": self.prefix,
                },
                "alert_preventive_cycle",
            )

        days = self._expiry_alert_days()
        if self.date_to and today <= self.date_to <= today + timedelta(days=days):
            self._emit_alert(
                "expiring",
                _("NCF próximo a vencer — %(company)s / %(prefix)s")
                % {"company": self.company_id.name, "prefix": self.prefix},
                "alert_expiring_cycle",
            )

    @api.model
    def _cron_process_ncf_range_alerts(self):
        """Cron: alertas por compañía, sin mezclar empresas."""
        Company = self.env["res.company"].sudo()
        for company in Company.search([]):
            ranges = self.sudo().search(
                [
                    ("company_id", "=", company.id),
                    ("state", "!=", "draft"),
                ]
            )
            for rng in ranges.with_company(company).with_context(
                allowed_company_ids=company.ids
            ):
                rng._process_alerts()
        return True
