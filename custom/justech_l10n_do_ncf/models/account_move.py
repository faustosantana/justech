from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    _justech_ncf_unique_index = "account_move_justech_do_ncf_company_uniq"

    justech_do_document_type_id = fields.Many2one(
        "justech.do.fiscal.document.type",
        string="Tipo de comprobante fiscal",
        copy=False,
    )
    justech_do_ncf = fields.Char(
        string="Número de Comprobante Fiscal",
        copy=False,
        index=True,
    )
    justech_do_ncf_range_id = fields.Many2one(
        "justech.do.ncf.range",
        string="Rango NCF",
        copy=False,
    )
    justech_do_ncf_voided = fields.Boolean(
        string="NCF anulado",
        copy=False,
    )
    justech_do_ncf_void_reason = fields.Text(string="Motivo de anulación", copy=False)
    justech_do_ncf_void_date = fields.Date(string="Fecha de anulación", copy=False)
    justech_do_origin_ncf = fields.Char(
        string="NCF de origen",
        help="NCF referenciado en notas de crédito o débito.",
        copy=False,
    )
    justech_do_ncf_modified = fields.Char(
        string="NCF documento modificado",
        help="NCF del comprobante original en notas de crédito/débito (DGII 606/607 col. F).",
        copy=False,
    )
    justech_do_dgii_line_status = fields.Selection(
        selection=[
            ("1", "Válido"),
            ("2", "Anulado"),
        ],
        string="Estatus DGII",
        default="1",
        copy=False,
        help="Estatus de la línea en archivos DGII (1=válido, 2=anulado).",
    )
    justech_do_include_in_dgii = fields.Boolean(
        string="Incluir en reportes DGII",
        default=True,
        copy=False,
        tracking=True,
        help="Si está desmarcado, el documento no se exporta en formatos DGII (606, 607, 608).",
    )
    justech_do_dgii_exclusion_reason = fields.Text(
        string="Motivo de exclusión fiscal",
        copy=False,
        help="Razón por la cual el documento queda fuera de los reportes DGII.",
    )
    justech_do_dgii_fiscal_state = fields.Selection(
        selection=[
            ("valid", "Válido"),
            ("incomplete", "Incompleto"),
            ("excluded", "Excluido"),
            ("cancelled", "Anulado"),
        ],
        string="Estado fiscal DGII",
        default="incomplete",
        index=True,
        copy=False,
        help="Clasificación del documento para exportación DGII.",
    )
    justech_do_ncf_cancel_type = fields.Selection(
        selection=[
            ("01", "Secuencia no utilizada"),
            ("02", "Errores de impresión"),
            ("03", "Impresión defectuosa"),
            ("04", "Corrección de información"),
            ("05", "Cambio de productos"),
            ("06", "Devolución de productos"),
            ("07", "Omisión de productos"),
            ("08", "Errores en secuencias NCF"),
            ("09", "Cese de operaciones"),
            ("10", "Pérdida o hurto de talonario"),
        ],
        string="Tipo de anulación DGII",
        copy=False,
        help="Código DGII formato 608 / anulación de comprobante.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reversed_entry_id") and vals.get("move_type") in (
                "in_refund",
                "out_refund",
            ):
                origin = self.env["account.move"].browse(vals["reversed_entry_id"])
                if origin.justech_do_ncf:
                    vals.setdefault("justech_do_origin_ncf", origin.justech_do_ncf)
                    vals.setdefault("justech_do_ncf_modified", origin.justech_do_ncf)
            if (
                not vals.get("justech_do_document_type_id")
                and vals.get("move_type") == "out_invoice"
                and vals.get("partner_id")
                and not vals.get("debit_origin_id")
            ):
                partner = self.env["res.partner"].browse(vals["partner_id"])
                doc = partner.justech_do_get_default_sale_document_type()
                if doc:
                    vals["justech_do_document_type_id"] = doc.id
        return super().create(vals_list)

    @api.onchange("partner_id")
    def _onchange_partner_justech_do_document_type(self):
        if self.move_type != "out_invoice" or self.debit_origin_id:
            return
        if not self.partner_id:
            self.justech_do_document_type_id = False
            return
        if self.justech_do_document_type_id:
            return
        self.justech_do_document_type_id = self.partner_id.justech_do_get_default_sale_document_type()

    @api.onchange("reversed_entry_id")
    def _onchange_reversed_entry_ncf_modified(self):
        if self.reversed_entry_id and self.move_type in ("in_refund", "out_refund"):
            self.justech_do_origin_ncf = self.reversed_entry_id.justech_do_ncf
            self.justech_do_ncf_modified = self.reversed_entry_id.justech_do_ncf

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
            partner_default = self.partner_id.justech_do_get_default_sale_document_type()
            if partner_default:
                return partner_default
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
            if move.move_type == "in_refund" and move.reversed_entry_id:
                origin_ncf = move.reversed_entry_id.justech_do_ncf
                move.justech_do_origin_ncf = origin_ncf
                if not move.justech_do_ncf_modified:
                    move.justech_do_ncf_modified = origin_ncf

    def _justech_moves_for_ncf_on_post(self, soft=True):
        """Moves that will be posted in this _post() call and need NCF assignment."""
        moves = self.filtered(lambda m: m.state == "draft")
        if soft:
            today = fields.Date.context_today(self)
            moves = moves.filtered(lambda m: not m.date or m.date <= today)
        return moves

    def _post(self, soft=True):
        self._justech_moves_for_ncf_on_post(soft)._justech_assign_ncf_before_post()
        return super()._post(soft=soft)

    def action_post(self):
        return super().action_post()

    def action_void_ncf(self):
        if not self.env.user.has_group(
            "justech_l10n_do_base.group_justech_do_fiscal_manager"
        ):
            raise AccessError(_("Solo los responsables fiscales pueden anular comprobantes."))
        Consumption = self.env["justech.do.ncf.consumption"]
        now = fields.Datetime.now()
        for move in self:
            if move.state != "posted":
                raise UserError(_("Solo documentos publicados pueden anular el comprobante fiscal."))
            if not move.justech_do_ncf:
                raise UserError(_("No hay comprobante fiscal para anular."))
            if move.justech_do_ncf_voided:
                raise UserError(_("El comprobante fiscal ya está anulado."))
            reason = (move.justech_do_ncf_void_reason or "").strip()
            if not reason:
                raise UserError(_("Debe indicar el motivo de anulación antes de anular el comprobante fiscal."))
            move.write(
                {
                    "justech_do_ncf_voided": True,
                    "justech_do_ncf_void_date": fields.Date.context_today(move),
                    "justech_do_dgii_line_status": "2",
                    "justech_do_dgii_fiscal_state": "cancelled",
                    "justech_do_include_in_dgii": False,
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
