import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

NCF_FULL_RE = re.compile(r"^[BE][0-9]{2}[0-9]{8}$")


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
        string="Journals",
        domain="[('company_id', '=', company_id)]",
    )
    authorization_number = fields.Char(string="DGII Authorization")
    sequence_start = fields.Integer(required=True, default=1)
    sequence_end = fields.Integer(required=True)
    next_sequence = fields.Integer(required=True, default=1)
    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("depleted", "Depleted"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    remaining_count = fields.Integer(compute="_compute_remaining")
    consumption_ids = fields.One2many(
        "justech.do.ncf.consumption",
        "range_id",
        string="Consumption",
    )

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

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to < rec.date_from:
                raise ValidationError(_("End date must be after start date."))

    @api.model
    def _validate_ncf_format(self, ncf):
        ncf = (ncf or "").strip().upper().replace(" ", "")
        if not NCF_FULL_RE.match(ncf):
            raise ValidationError(
                _("Invalid NCF format. Expected 11 characters (e.g. B0100000001).")
            )
        return ncf

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
        self._check_usable()
        ncf = self.document_type_id.format_ncf(self.next_sequence)
        self.env["justech.do.ncf.consumption"].create(
            {
                "range_id": self.id,
                "move_id": move.id,
                "ncf": ncf,
                "sequence_number": self.next_sequence,
                "state": "consumed",
            }
        )
        next_seq = self.next_sequence + 1
        vals = {"next_sequence": next_seq}
        if next_seq > self.sequence_end:
            vals["state"] = "depleted"
        self.write(vals)
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
