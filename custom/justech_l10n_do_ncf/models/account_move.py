from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    _justech_ncf_unique_index = "account_move_justech_do_ncf_company_uniq"

    justech_do_document_type_id = fields.Many2one(
        "justech.do.fiscal.document.type",
        string="Fiscal Document Type",
        copy=False,
    )
    justech_do_ncf = fields.Char(
        string="NCF",
        copy=False,
        index=True,
    )
    justech_do_ncf_range_id = fields.Many2one(
        "justech.do.ncf.range",
        string="NCF Range",
        copy=False,
    )
    justech_do_ncf_voided = fields.Boolean(
        string="NCF Voided",
        copy=False,
    )
    justech_do_ncf_void_reason = fields.Text(string="Void Reason", copy=False)
    justech_do_ncf_void_date = fields.Date(copy=False)
    justech_do_origin_ncf = fields.Char(
        string="Origin NCF",
        help="Referenced NCF for credit/debit notes.",
        copy=False,
    )

    def init(self):
        super().init()
        self._cr.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {self._justech_ncf_unique_index}
            ON account_move (company_id, justech_do_ncf)
            WHERE state = 'posted'
              AND justech_do_ncf IS NOT NULL
              AND justech_do_ncf != ''
            """
        )

    @api.model
    def _justech_fiscal_enabled(self):
        company = self.env.company
        return company.country_id.code == "DO" and company.justech_do_fiscal_enabled

    def _justech_resolve_document_type(self):
        self.ensure_one()
        if self.justech_do_document_type_id:
            return self.justech_do_document_type_id
        journal = self.journal_id
        if self.move_type == "out_refund":
            return self.env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
        if self.move_type == "out_invoice" and self.debit_origin_id:
            return self.env.ref("justech_l10n_do_base.doc_type_b03", raise_if_not_found=False)
        if self.move_type == "out_invoice":
            if self.partner_id.justech_do_has_rnc():
                return self.env.ref("justech_l10n_do_base.doc_type_b01", raise_if_not_found=False)
            return self.env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
        if self.move_type == "in_invoice" and journal.justech_do_default_document_type_id:
            doc = journal.justech_do_default_document_type_id
            if doc.prefix in ("B11", "B13"):
                return doc
        return False

    def _justech_should_auto_assign_ncf(self):
        self.ensure_one()
        if not self._justech_fiscal_enabled():
            return False
        if not self.journal_id.justech_do_use_ncf:
            return False
        doc = self._justech_resolve_document_type()
        if not doc or not doc.auto_assign_on_post:
            return False
        if self.move_type in ("out_invoice", "out_refund"):
            return True
        if self.move_type == "in_invoice" and doc.prefix in ("B11", "B13"):
            return True
        return False

    def _justech_validate_manual_ncf(self):
        self.ensure_one()
        if not self.justech_do_ncf:
            return
        ncf = self.env["justech.do.ncf.range"]._validate_ncf_format(self.justech_do_ncf)
        self.justech_do_ncf = ncf
        prefix, seq = self.env["justech.do.fiscal.document.type"].parse_ncf(ncf)
        if self.justech_do_document_type_id and prefix != self.justech_do_document_type_id.prefix:
            raise ValidationError(_("NCF prefix does not match document type."))
        self._justech_check_duplicate_ncf(ncf)

    def _justech_check_duplicate_ncf(self, ncf):
        self.ensure_one()
        dup = self.search(
            [
                ("id", "!=", self.id),
                ("company_id", "=", self.company_id.id),
                ("justech_do_ncf", "=", ncf),
                ("state", "=", "posted"),
                ("justech_do_ncf_voided", "=", False),
            ],
            limit=1,
        )
        if dup:
            raise ValidationError(
                _("NCF %(ncf)s is already used on %(move)s.", ncf=ncf, move=dup.name)
            )

    def _justech_assign_ncf_before_post(self):
        for move in self:
            if move.state != "draft":
                continue
            if not move._justech_fiscal_enabled():
                continue
            if move.justech_do_ncf_voided:
                continue
            doc = move._justech_resolve_document_type()
            if doc and not move.justech_do_document_type_id:
                move.justech_do_document_type_id = doc.id
            if doc and doc.requires_vat and move.move_type in ("out_invoice", "out_refund"):
                if not move.partner_id.justech_do_has_rnc():
                    raise UserError(
                        _("Document type %(doc)s requires a customer RNC.", doc=doc.prefix)
                    )
            if move.justech_do_ncf:
                move._justech_validate_manual_ncf()
                continue
            if not move._justech_should_auto_assign_ncf():
                if move.journal_id.justech_do_use_ncf and move.move_type in (
                    "out_invoice",
                    "out_refund",
                ):
                    raise UserError(_("NCF is required before posting this invoice."))
                continue
            doc = move.justech_do_document_type_id
            lock_code = int(doc.code) if doc.code.isdigit() else 0
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)",
                [move.company_id.id, lock_code],
            )
            ncf_range = self.env["justech.do.ncf.range"]._find_active_range_for_update(
                doc, move.journal_id, move.company_id
            )
            if not ncf_range:
                raise UserError(
                    _("No active NCF range for document type %(prefix)s.", prefix=doc.prefix)
                )
            ncf = ncf_range.consume_next(move)
            move.write(
                {
                    "justech_do_ncf": ncf,
                    "justech_do_ncf_range_id": ncf_range.id,
                    "justech_do_document_type_id": doc.id,
                }
            )
            if move.move_type == "out_refund" and move.reversed_entry_id:
                move.justech_do_origin_ncf = move.reversed_entry_id.justech_do_ncf

    def action_post(self):
        self._justech_assign_ncf_before_post()
        return super().action_post()

    def action_void_ncf(self):
        if not self.env.user.has_group(
            "justech_l10n_do_base.group_justech_do_fiscal_manager"
        ):
            raise AccessError(_("Only fiscal managers can void NCF."))
        Consumption = self.env["justech.do.ncf.consumption"]
        now = fields.Datetime.now()
        for move in self:
            if move.state != "posted":
                raise UserError(_("Only posted moves can void NCF."))
            if not move.justech_do_ncf:
                raise UserError(_("No NCF to void."))
            if move.justech_do_ncf_voided:
                raise UserError(_("NCF is already voided."))
            reason = (move.justech_do_ncf_void_reason or "").strip()
            if not reason:
                raise UserError(_("A void reason is required before voiding NCF."))
            move.write(
                {
                    "justech_do_ncf_voided": True,
                    "justech_do_ncf_void_date": fields.Date.context_today(move),
                }
            )
            consumption = Consumption.search(
                [
                    ("move_id", "=", move.id),
                    ("ncf", "=", move.justech_do_ncf),
                    ("state", "=", "consumed"),
                ],
                limit=1,
            )
            if consumption:
                consumption.write(
                    {
                        "state": "voided",
                        "void_user_id": self.env.user.id,
                        "void_datetime": now,
                        "void_reason": reason,
                    }
                )

    @api.constrains("justech_do_ncf", "company_id", "state")
    def _check_ncf_unique_constraint(self):
        for move in self.filtered(lambda m: m.justech_do_ncf and m.state == "posted"):
            move._justech_check_duplicate_ncf(move.justech_do_ncf)
