from odoo import api, fields, models
from odoo.exceptions import ValidationError


class JustechDoFiscalDocumentType(models.Model):
    _name = "justech.do.fiscal.document.type"
    _description = "Dominican Fiscal Document Type (NCF)"
    _order = "prefix, code"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        string="Type Code",
        required=True,
        size=2,
        help="Two-digit DGII type code (01, 02, 11, etc.)",
    )
    prefix = fields.Char(
        required=True,
        size=3,
        help="NCF prefix including series letter (B01, B02, E31 future)",
    )
    series = fields.Char(default="B", size=1, required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
    )
    is_sale_document = fields.Boolean(string="Sales Document")
    is_purchase_document = fields.Boolean(string="Purchase Document")
    is_credit_note = fields.Boolean(string="Credit Note")
    is_debit_note = fields.Boolean(string="Debit Note")
    requires_vat = fields.Boolean(
        string="Requires RNC",
        help="If set, partner must have VAT/RNC (e.g. B01).",
    )
    auto_assign_on_post = fields.Boolean(
        string="Auto-assign NCF on Post",
        default=True,
        help="System assigns next NCF from range when posting.",
    )
    move_type = fields.Selection(
        selection=[
            ("out_invoice", "Customer Invoice"),
            ("out_refund", "Customer Credit Note"),
            ("in_invoice", "Vendor Bill"),
            ("in_refund", "Vendor Credit Note"),
        ],
        string="Default Move Type",
    )

    _sql_constraints = [
        (
            "prefix_company_uniq",
            "unique(prefix, company_id)",
            "Document type prefix must be unique per company.",
        ),
    ]

    @api.constrains("code", "prefix", "series")
    def _check_codes(self):
        for doc in self:
            if not doc.code.isdigit() or len(doc.code) != 2:
                raise ValidationError("Document type code must be two digits.")
            if len(doc.prefix) != 3:
                raise ValidationError("Prefix must be 3 characters (e.g. B01).")
            if doc.prefix[0] != doc.series:
                raise ValidationError("Prefix series letter must match series field.")

    def format_ncf(self, sequence_number):
        """Return 11-char NCF: prefix (3) + sequence (8)."""
        self.ensure_one()
        return f"{self.prefix}{int(sequence_number):08d}"

    @api.model
    def parse_ncf(self, ncf):
        """Parse NCF into prefix and sequence number."""
        ncf = (ncf or "").strip().upper().replace(" ", "")
        if len(ncf) != 11:
            return False, False
        return ncf[:3], int(ncf[3:])
