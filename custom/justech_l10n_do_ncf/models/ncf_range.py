from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class JustechDoNcfRange(models.Model):
    _name = "justech.do.ncf.range"
    _description = "Dominican NCF Authorized Range"
    _order = "date_to, prefix"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    document_type_id = fields.Many2one(
        "justech.do.fiscal.document.type",
        required=True,
        ondelete="restrict",
    )
    prefix = fields.Char(related="document_type_id.prefix", store=True)
    journal_ids = fields.Many2many(
        "account.journal",
        string="Diarios",
        domain="[('company_id', '=', company_id)]",
    )
    authorization_number = fields.Char(string="Autorización DGII")
    sequence_start = fields.Integer(string="Secuencia inicial", required=True, default=1)
    sequence_end = fields.Integer(string="Secuencia final", required=True)
    next_sequence = fields.Integer(string="Próxima secuencia", required=True, default=1)
    date_from = fields.Date(string="Vigente desde", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="Fecha de vencimiento", required=True)
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
    )
    remaining_count = fields.Integer(string="Disponibles", compute="_compute_remaining")
    pct_used = fields.Float(string="% Consumido", compute="_compute_pct_used")
    next_ncf_display = fields.Char(string="Próximo NCF", compute="_compute_next_ncf_display")
    consumption_ids = fields.One2many(
        "justech.do.ncf.consumption",
        "range_id",
        string="Consumo",
    )

    STANDARD_RANGE_NAMES = {
        "B01": "B01 Factura de Crédito Fiscal",
        "B02": "B02 Factura de Consumo",
        "B03": "B03 Nota de Débito",
        "B04": "B04 Nota de Crédito",
        "B11": "B11 Comprobante de Compras",
        "B13": "B13 Gastos Menores",
        "B14": "B14 Regímenes Especiales de Tributación",
        "B15": "B15 Comprobante Gubernamental",
        "B17": "B17 Comprobante para Pagos al Exterior",
    }

    _sql_constraints = [
        (
            "sequence_check",
            "CHECK(sequence_start > 0 AND sequence_end >= sequence_start)",
            "Invalid sequence bounds.",
        ),
    ]

    @api.depends("next_sequence", "sequence_end", "state")
    def _compute_remaining(self):
        for rec in self:
            if rec.state in ("depleted", "cancelled"):
                rec.remaining_count = 0
            else:
                rec.remaining_count = max(0, rec.sequence_end - rec.next_sequence + 1)

    @api.depends("sequence_start", "sequence_end", "next_sequence", "state")
    def _compute_pct_used(self):
        for rec in self:
            total = max(1, rec.sequence_end - rec.sequence_start + 1)
            if rec.state in ("depleted", "cancelled"):
                rec.pct_used = 100.0
            else:
                used = max(0, rec.next_sequence - rec.sequence_start)
                rec.pct_used = min(100.0, round(100.0 * used / total, 1))

    @api.depends("prefix", "next_sequence")
    def _compute_next_ncf_display(self):
        for rec in self:
            if rec.prefix and rec.next_sequence:
                rec.next_ncf_display = f"{rec.prefix}{int(rec.next_sequence):08d}"
            else:
                rec.next_ncf_display = False

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

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_set_draft(self):
        self.write({"state": "draft"})

    def _check_usable(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.state != "active":
            raise UserError(_("NCF range %(name)s is not active.", name=self.name))
        if today > self.date_to:
            self.state = "expired"
            raise UserError(_("NCF range %(name)s has expired.", name=self.name))
        if self.next_sequence > self.sequence_end:
            self.state = "depleted"
            raise UserError(_("NCF range %(name)s is depleted.", name=self.name))

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
        if state != "active":
            raise UserError(_("NCF range %(name)s is not active.", name=self.name))
        if today > date_to:
            self.env.cr.execute(
                "UPDATE justech_do_ncf_range SET state = 'expired' WHERE id = %s",
                [self.id],
            )
            raise UserError(_("NCF range %(name)s has expired.", name=self.name))
        if next_seq > seq_end:
            self.env.cr.execute(
                "UPDATE justech_do_ncf_range SET state = 'depleted' WHERE id = %s",
                [self.id],
            )
            raise UserError(_("NCF range %(name)s is depleted.", name=self.name))
        doc_type = self.env["justech.do.fiscal.document.type"].browse(doc_type_id)
        ncf = doc_type.format_ncf(next_seq)
        self.env["justech.do.ncf.consumption"].create(
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
        ranges = ranges.filtered(lambda r: r.date_to >= today and r.next_sequence <= r.sequence_end)
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
