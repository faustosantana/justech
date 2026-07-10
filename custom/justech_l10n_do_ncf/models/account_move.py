from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


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
    # Lectura histórica segura (solo UI) — valores vía Fiscal Data Provider; nunca escriben.
    fiscal_document_type_display = fields.Char(
        string="Tipo de comprobante fiscal",
        compute="_compute_fiscal_display_fields",
        readonly=True,
    )
    fiscal_ncf_display = fields.Char(
        string="NCF",
        compute="_compute_fiscal_display_fields",
        readonly=True,
        help="NCF de solo lectura vía Fiscal Data Provider (Justech → Adel/latam → Odoo).",
    )
    fiscal_status_display = fields.Char(
        string="Estado fiscal",
        compute="_compute_fiscal_display_fields",
        readonly=True,
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

    @api.depends(
        "justech_do_ncf",
        "justech_do_document_type_id",
        "justech_do_ncf_voided",
        "justech_do_dgii_fiscal_state",
        "justech_do_include_in_dgii",
        "justech_do_dgii_line_status",
        "l10n_latam_document_number",
        "l10n_latam_document_type_id",
        "ref",
        "payment_reference",
        "name",
        "move_type",
    )
    def _compute_fiscal_display_fields(self):
        """UI-only: never writes stored fiscal fields; safe if legacy layers missing."""
        fdp = self.env["justech.do.fiscal.data.provider"]
        for move in self:
            ncf = ""
            doc_type = ""
            status = ""
            try:
                ncf = fdp.get_ncf(move) or ""
                doc_type = fdp.get_document_type_name(move) or ""
                if not doc_type and ncf:
                    doc_type = fdp.get_document_type_prefix(move) or ""
                src = fdp.get_supported_sources(move)
                voided = False
                try:
                    voided = bool(fdp.is_voided(move))
                except Exception:
                    voided = bool(getattr(move, "justech_do_ncf_voided", False))
                include_dgii = True
                if "justech_do_include_in_dgii" in move._fields:
                    include_dgii = bool(move.justech_do_include_in_dgii)
                dgii_state = ""
                if "justech_do_dgii_fiscal_state" in move._fields:
                    dgii_state = move.justech_do_dgii_fiscal_state or ""

                if voided or dgii_state == "cancelled":
                    status = "Anulado"
                elif not include_dgii or dgii_state == "excluded":
                    status = "Excluido"
                elif ncf and src == "adel_latam":
                    # Histórico Adel con NCF válido: nunca "Incompleto"
                    status = "Histórico compatible"
                elif ncf:
                    status = "Válido"
                else:
                    # Sin NCF: no exponer el default DGII "incomplete" en UI
                    status = ""
            except Exception:
                # Nunca tumbar el formulario por lectura fiscal
                ncf = ncf or ""
                doc_type = doc_type or ""
                status = status or ""
            move.fiscal_ncf_display = ncf
            move.fiscal_document_type_display = doc_type
            move.fiscal_status_display = status

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
        return self.env["justech.do.fiscal.config.service"].is_fiscal_enabled(
            self.env.company
        )

    def _justech_resolve_document_type(self):
        self.ensure_one()
        return self.env["justech.do.ncf.document.type.resolver.service"].resolve_for_move(
            self
        )

    def _justech_doc_supports_auto_ncf(self, doc):
        self.ensure_one()
        return self.env[
            "justech.do.ncf.document.type.resolver.service"
        ].doc_supports_auto_ncf(self, doc)

    def _justech_should_auto_assign_ncf(self):
        self.ensure_one()
        return self.env[
            "justech.do.ncf.document.type.resolver.service"
        ].should_auto_assign_ncf(self)

    def _justech_validate_manual_ncf(self):
        self.ensure_one()
        self.env["justech.do.ncf.duplicate.service"].validate_manual_ncf(self)

    def _justech_check_duplicate_ncf(self, ncf):
        self.ensure_one()
        self.env["justech.do.ncf.duplicate.service"].check_duplicate(self, ncf)

    def _justech_assign_ncf_before_post(self):
        self.env["justech.do.ncf.assignment.service"].assign_before_post(self)

    def _justech_moves_for_ncf_on_post(self, soft=True):
        return self.env["justech.do.ncf.assignment.service"].moves_for_post(self, soft)

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
