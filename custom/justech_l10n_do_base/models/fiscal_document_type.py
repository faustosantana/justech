from odoo import api, fields, models
from odoo.exceptions import ValidationError


class JustechDoFiscalDocumentType(models.Model):
    _name = "justech.do.fiscal.document.type"
    _description = "Dominican Fiscal Document Type (NCF)"
    _order = "prefix, code"

    # Serie B — comprobantes tradicionales DGII (NG 06-2018)
    SALE_NCF_PREFIXES = ("B01", "B02", "B03", "B04", "B12", "B14", "B15", "B16")
    PURCHASE_NCF_PREFIXES = ("B11", "B13", "B17")
    CONSUMER_NCF_PREFIXES = ("B02", "B12", "E32", "E33")
    ALL_NCF_PREFIXES = SALE_NCF_PREFIXES + PURCHASE_NCF_PREFIXES

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

    @api.depends("prefix", "name")
    def _compute_display_name(self):
        for doc in self:
            if doc.prefix and doc.name:
                doc.display_name = f"{doc.prefix} - {doc.name}"
            else:
                doc.display_name = doc.name or doc.prefix or ""

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
        from odoo.addons.justech_l10n_do_base.validators import ncf_format

        return ncf_format.parse_ncf(ncf)

    def is_sale_ncf(self):
        self.ensure_one()
        return self.prefix in self.SALE_NCF_PREFIXES

    def is_purchase_ncf(self):
        self.ensure_one()
        return self.prefix in self.PURCHASE_NCF_PREFIXES

    @api.model
    def get_by_prefix(self, prefix, company=None):
        company = company or self.env.company
        return self.search(
            [("prefix", "=", prefix), ("company_id", "in", (False, company.id))],
            limit=1,
        )
