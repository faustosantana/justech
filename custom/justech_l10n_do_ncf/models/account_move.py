from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    # Legacy (pre-2.3.0): company+NCF — too strict for purchases.
    _justech_ncf_unique_index = "account_move_justech_do_ncf_company_uniq"
    _justech_ncf_sale_unique_index = "account_move_justech_do_ncf_sale_uniq"
    _justech_ncf_purchase_unique_index = "account_move_justech_do_ncf_purchase_uniq"

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
    fiscal_income_expense_type_display = fields.Char(
        string="Tipo de ingreso / costo y gasto",
        compute="_compute_fiscal_display_fields",
        readonly=True,
        help="Solo lectura vía Fiscal Data Provider (ingreso 607 o costo/gasto 606).",
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
    justech_do_can_void_ncf = fields.Boolean(
        string="Puede anular NCF",
        compute="_compute_justech_do_can_void_ncf",
    )
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
    justech_do_purchase_registration_mode = fields.Selection(
        selection=[
            ("received", "Documento recibido del proveedor"),
            ("issued", "Comprobante emitido por la empresa"),
        ],
        string="Tipo de registro",
        default="received",
        copy=False,
        help="Compras: separar recepción LATAM vs emisión Justech (B11/B13/B17).",
    )
    justech_do_purchase_emission_status = fields.Char(
        string="Estado del rango (compras)",
        compute="_compute_purchase_emission_ui",
    )
    justech_do_purchase_next_ncf = fields.Char(
        string="Próximo NCF (compras)",
        compute="_compute_purchase_emission_ui",
    )
    # Clasificación 606 por factura (no regla rígida del proveedor).
    justech_do_expense_type_id = fields.Many2one(
        "justech.do.dgii.expense.type",
        string="Tipo de costos y gastos",
        copy=True,
        index=True,
        domain="[('active', '=', True), ('applies_to_606', '=', True)]",
        help="Clasificación DGII 606 por documento. Editable en borrador.",
    )
    justech_do_expense_type_606 = fields.Char(
        string="Código costos/gastos 606",
        related="justech_do_expense_type_id.code",
        store=True,
        index=True,
    )
    justech_do_expense_type_manual = fields.Boolean(
        string="Tipo de costos/gastos manual",
        copy=False,
        help="Si es True, las sugerencias no sobrescriben la selección del usuario.",
    )
    justech_do_expense_type_suggestion_label = fields.Char(
        string="Sugerencia costos/gastos",
        compute="_compute_expense_type_suggestion_label",
    )

    @api.depends(
        "justech_do_purchase_registration_mode",
        "justech_do_document_type_id",
        "company_id",
    )
    def _compute_purchase_emission_ui(self):
        Config = self.env["justech.do.purchase.emission.config"]
        for move in self:
            move.justech_do_purchase_emission_status = False
            move.justech_do_purchase_next_ncf = False
            if (
                move.move_type not in ("in_invoice", "in_refund")
                or move.justech_do_purchase_registration_mode != "issued"
                or not move.justech_do_document_type_id
            ):
                continue
            cfg = Config.get_for(move.company_id, move.justech_do_document_type_id)
            if not cfg:
                move.justech_do_purchase_emission_status = "Sin rango autorizado"
                continue
            move.justech_do_purchase_emission_status = cfg.status_label
            if cfg.emission_enabled:
                move.justech_do_purchase_next_ncf = cfg.next_ncf

    @api.onchange("justech_do_purchase_registration_mode")
    def _onchange_purchase_registration_mode(self):
        if self.move_type not in ("in_invoice", "in_refund"):
            return
        if self.justech_do_purchase_registration_mode == "received":
            self.justech_do_document_type_id = False
            self.justech_do_ncf = False
            self.justech_do_ncf_range_id = False
        elif self.justech_do_purchase_registration_mode == "issued":
            if "l10n_latam_document_type_id" in self._fields:
                self.l10n_latam_document_type_id = False
            if "l10n_latam_document_number" in self._fields:
                self.l10n_latam_document_number = False

    @api.depends(
        "partner_id",
        "justech_do_expense_type_manual",
        "justech_do_expense_type_id",
        "move_type",
    )
    def _compute_expense_type_suggestion_label(self):
        # UI: la línea «Sugerencia» se eliminó del formulario de compras.
        # No recalcular texto visible; el usuario elige Tipo de costos y gastos.
        for move in self:
            move.justech_do_expense_type_suggestion_label = False

    def _justech_expense_type_from_code(self, code):
        code = (code or "").strip()
        if not code:
            return self.env["justech.do.dgii.expense.type"]
        return self.env["justech.do.dgii.expense.type"].search(
            [("code", "=", code)], limit=1
        )

    def _justech_suggest_expense_type(self):
        """Sugerencia no bloqueante: historial proveedor → default Adel → B13→06."""
        self.ensure_one()
        if self.move_type not in ("in_invoice", "in_refund") or not self.partner_id:
            return self.env["justech.do.dgii.expense.type"]
        Expense = self.env["justech.do.dgii.expense.type"]
        company = self.company_id or self.env.company
        hist = self.search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("company_id", "=", company.id),
                ("move_type", "in", ("in_invoice", "in_refund")),
                ("state", "=", "posted"),
                ("justech_do_expense_type_id", "!=", False),
                ("id", "!=", self.id or 0),
            ],
            order="invoice_date desc, id desc",
            limit=1,
        )
        if hist.justech_do_expense_type_id:
            return hist.justech_do_expense_type_id
        # Fallback Adel / latam en historial
        hist_latam = self.search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("company_id", "=", company.id),
                ("move_type", "in", ("in_invoice", "in_refund")),
                ("state", "=", "posted"),
                ("id", "!=", self.id or 0),
            ],
            order="invoice_date desc, id desc",
            limit=5,
        )
        for move in hist_latam:
            code = False
            if "l10n_do_expense_type" in move._fields:
                code = move.l10n_do_expense_type
            if code:
                found = self._justech_expense_type_from_code(code)
                if found:
                    return found
        partner_code = False
        if "l10n_do_expense_type" in self.partner_id._fields:
            partner_code = self.partner_id.l10n_do_expense_type
        if partner_code:
            found = self._justech_expense_type_from_code(partner_code)
            if found:
                return found
        prefix = False
        if self.justech_do_document_type_id:
            prefix = self.justech_do_document_type_id.prefix
        elif "l10n_latam_document_type_id" in self._fields and self.l10n_latam_document_type_id:
            prefix = self.l10n_latam_document_type_id.doc_code_prefix
        if prefix == "B13":
            return self._justech_expense_type_from_code("06")
        return Expense.browse()

    def _justech_sync_expense_type_to_latam(self, expense_type):
        """Mantener compatibilidad Adel/606 histórico vía l10n_do_expense_type."""
        self.ensure_one()
        if "l10n_do_expense_type" not in self._fields:
            return {}
        code = expense_type.code if expense_type else False
        if self.l10n_do_expense_type != code:
            return {"l10n_do_expense_type": code}
        return {}

    def _justech_apply_expense_suggestion(self, force=False):
        """Desactivado: no autocompletar tipo de costos/gastos.

        Se conserva el helper y ``_justech_suggest_expense_type`` por si un
        flujo administrativo futuro lo necesita con ``force=True`` explícito.
        """
        self.ensure_one()
        if not force:
            return {}
        if self.move_type not in ("in_invoice", "in_refund"):
            return {}
        if self.justech_do_expense_type_manual and self.justech_do_expense_type_id:
            return {}
        if self.justech_do_expense_type_id:
            return {}
        suggested = self._justech_suggest_expense_type()
        if not suggested:
            return {}
        vals = {"justech_do_expense_type_id": suggested.id}
        vals.update(self._justech_sync_expense_type_to_latam(suggested))
        return vals

    @api.onchange("partner_id", "justech_do_document_type_id", "l10n_latam_document_type_id")
    def _onchange_justech_expense_type_suggest(self):
        # No sugerir ni escribir justech_do_expense_type_id automáticamente.
        # Solo re-sincroniza Adel si el usuario ya eligió un tipo manualmente.
        if self.move_type not in ("in_invoice", "in_refund"):
            return
        if self.justech_do_expense_type_manual and self.justech_do_expense_type_id:
            sync = self._justech_sync_expense_type_to_latam(self.justech_do_expense_type_id)
            for key, val in sync.items():
                setattr(self, key, val)

    @api.onchange("justech_do_expense_type_id")
    def _onchange_justech_expense_type_manual(self):
        if self.move_type not in ("in_invoice", "in_refund"):
            return
        if self.justech_do_expense_type_id:
            self.justech_do_expense_type_manual = True
            sync = self._justech_sync_expense_type_to_latam(self.justech_do_expense_type_id)
            for key, val in sync.items():
                setattr(self, key, val)

    def _justech_purchase_received_latam_domain(self):
        prefixes = list(
            self.env["justech.do.fiscal.document.type"].PURCHASE_RECEIVED_DOC_PREFIXES
        )
        return [("doc_code_prefix", "in", prefixes)]

    def _justech_is_purchase_received(self):
        self.ensure_one()
        return self.move_type in ("in_invoice", "in_refund") and (
            self.justech_do_purchase_registration_mode or "received"
        ) == "received"

    def _justech_is_purchase_issued(self):
        self.ensure_one()
        return (
            self.move_type in ("in_invoice", "in_refund")
            and self.justech_do_purchase_registration_mode == "issued"
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
        "justech_do_expense_type_id",
        "justech_do_expense_type_606",
        "l10n_do_expense_type",
    )
    def _compute_fiscal_display_fields(self):
        """UI-only: never writes stored fiscal fields; safe if legacy layers missing."""
        fdp = self.env["justech.do.fiscal.data.provider"]
        for move in self:
            ncf = ""
            doc_type = ""
            status = ""
            income_expense = ""
            try:
                ncf = fdp.get_ncf(move) or ""
                doc_type = fdp.get_document_type_name(move) or ""
                if not doc_type and ncf:
                    doc_type = fdp.get_document_type_prefix(move) or ""
                income_expense = fdp.get_income_expense_type_display(move) or ""
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
                income_expense = income_expense or ""
            move.fiscal_ncf_display = ncf
            move.fiscal_document_type_display = doc_type
            move.fiscal_status_display = status
            move.fiscal_income_expense_type_display = income_expense

    @api.model_create_multi
    def create(self, vals_list):
        Expense = self.env["justech.do.dgii.expense.type"]
        for vals in vals_list:
            if vals.get("move_type") in ("in_invoice", "in_refund", "in_receipt"):
                if vals.get("justech_do_document_type_id") or vals.get("justech_do_ncf"):
                    vals.setdefault(
                        "justech_do_purchase_registration_mode", "issued"
                    )
                else:
                    vals.setdefault(
                        "justech_do_purchase_registration_mode", "received"
                    )
            if vals.get("reversed_entry_id") and vals.get("move_type") in (
                "in_refund",
                "out_refund",
            ):
                origin = self.env["account.move"].browse(vals["reversed_entry_id"])
                if origin.justech_do_ncf:
                    vals.setdefault("justech_do_origin_ncf", origin.justech_do_ncf)
                    vals.setdefault("justech_do_ncf_modified", origin.justech_do_ncf)
                if vals.get("move_type") == "in_refund":
                    if origin.justech_do_expense_type_id:
                        vals.setdefault(
                            "justech_do_expense_type_id",
                            origin.justech_do_expense_type_id.id,
                        )
                    elif (
                        "l10n_do_expense_type" in origin._fields
                        and origin.l10n_do_expense_type
                    ):
                        found = Expense.search(
                            [("code", "=", origin.l10n_do_expense_type)], limit=1
                        )
                        if found:
                            vals.setdefault("justech_do_expense_type_id", found.id)
            # Mapear código Adel legado → Justech sin sobrescribir histórico posteado.
            if (
                vals.get("move_type") in ("in_invoice", "in_refund")
                and not vals.get("justech_do_expense_type_id")
                and vals.get("l10n_do_expense_type")
            ):
                found = Expense.search(
                    [("code", "=", vals["l10n_do_expense_type"])], limit=1
                )
                if found:
                    vals["justech_do_expense_type_id"] = found.id
            if vals.get("justech_do_expense_type_id") and "l10n_do_expense_type" in self._fields:
                exp = Expense.browse(vals["justech_do_expense_type_id"])
                vals.setdefault("l10n_do_expense_type", exp.code)
            if (
                not vals.get("justech_do_document_type_id")
                and vals.get("move_type") == "out_invoice"
                and vals.get("partner_id")
                and not vals.get("debit_origin_id")
            ):
                partner = self.env["res.partner"].browse(vals["partner_id"])
                company = self.env["res.company"].browse(
                    vals.get("company_id") or self.env.company.id
                )
                doc = partner.justech_do_get_default_sale_document_type(company=company)
                if doc:
                    vals["justech_do_document_type_id"] = doc.id
        moves = super().create(vals_list)
        for move in moves.filtered(
            lambda m: m.move_type in ("in_invoice", "in_refund")
            and not m.justech_do_expense_type_id
            and m.state == "draft"
        ):
            suggest_vals = move._justech_apply_expense_suggestion()
            if suggest_vals:
                # Sugerencia inicial: no marca manual (el usuario aún no eligió).
                move.with_context(justech_expense_suggest=True).write(suggest_vals)
        return moves

    def write(self, vals):
        vals = dict(vals)
        if "justech_do_expense_type_id" in vals and not self.env.context.get(
            "justech_expense_suggest"
        ):
            vals["justech_do_expense_type_manual"] = True
            exp = self.env["justech.do.dgii.expense.type"].browse(
                vals.get("justech_do_expense_type_id") or []
            )
            if "l10n_do_expense_type" in self._fields:
                vals.setdefault(
                    "l10n_do_expense_type", exp.code if exp else False
                )
        # No reactivar NCF anulado ni alterar traza 608 vía write genérico.
        if not self.env.context.get("justech_ncf_engine"):
            for move in self.filtered("justech_do_ncf_voided"):
                if vals.get("justech_do_ncf_voided") is False:
                    raise UserError(
                        _(
                            "No se puede reactivar un comprobante fiscal ya anulado "
                            "(%(ncf)s)."
                        )
                        % {"ncf": move._justech_get_issued_ncf() or move.name}
                    )
                if "justech_do_ncf" in vals and vals.get("justech_do_ncf") != move.justech_do_ncf:
                    raise UserError(
                        _(
                            "No se puede modificar ni reutilizar el NCF de un "
                            "comprobante ya anulado (%(ncf)s)."
                        )
                        % {"ncf": move.justech_do_ncf or move._justech_get_issued_ncf()}
                    )
                for fname in (
                    "justech_do_ncf_void_date",
                    "justech_do_ncf_void_reason",
                    "justech_do_ncf_cancel_type",
                ):
                    if fname in vals and vals.get(fname) != move[fname]:
                        raise UserError(
                            _("La anulación fiscal de %(doc)s es inmutable.")
                            % {"doc": move.display_name}
                        )
        return super().write(vals)

    def button_draft(self):
        """Restablecer a borrador sin reactivar ni reutilizar NCF anulado."""
        voided = self.filtered("justech_do_ncf_voided")
        snapshot = {
            move.id: {
                "justech_do_ncf": move.justech_do_ncf,
                "justech_do_ncf_voided": True,
                "justech_do_ncf_void_reason": move.justech_do_ncf_void_reason,
                "justech_do_ncf_void_date": move.justech_do_ncf_void_date,
                "justech_do_ncf_cancel_type": move.justech_do_ncf_cancel_type,
                "justech_do_dgii_line_status": "2",
                "justech_do_dgii_fiscal_state": "cancelled",
                "justech_do_include_in_dgii": False,
            }
            for move in voided
        }
        res = super().button_draft()
        for move in self.browse(list(snapshot)):
            move.with_context(justech_ncf_engine=True).write(snapshot[move.id])
        return res

    @api.onchange("partner_id")
    def _onchange_partner_justech_do_document_type(self):
        if self.move_type != "out_invoice" or self.debit_origin_id:
            return
        if not self.partner_id:
            self.justech_do_document_type_id = False
            return
        # Recalcular al cambiar cliente (no heredar el tipo del partner anterior).
        self.justech_do_document_type_id = False
        resolved = self.env[
            "justech.do.ncf.document.type.resolver.service"
        ].resolve_for_move(self)
        self.justech_do_document_type_id = resolved or False

    @api.onchange("reversed_entry_id")
    def _onchange_reversed_entry_ncf_modified(self):
        if self.reversed_entry_id and self.move_type in ("in_refund", "out_refund"):
            self.justech_do_origin_ncf = self.reversed_entry_id.justech_do_ncf
            self.justech_do_ncf_modified = self.reversed_entry_id.justech_do_ncf

    def init(self):
        super().init()
        # Drop legacy company-only unique index (blocks valid multi-vendor purchases).
        self._cr.execute(
            f"DROP INDEX IF EXISTS {self._justech_ncf_unique_index}"
        )
        # Ventas: único por empresa + NCF (posted, no anulado).
        self._cr.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {self._justech_ncf_sale_unique_index}
            ON account_move (company_id, justech_do_ncf)
            WHERE state = 'posted'
              AND justech_do_ncf IS NOT NULL
              AND justech_do_ncf != ''
              AND COALESCE(justech_do_ncf_voided, false) = false
              AND move_type IN ('out_invoice', 'out_refund', 'out_receipt')
            """
        )
        # Compras: único por empresa + proveedor + NCF (posted, no anulado).
        self._cr.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {self._justech_ncf_purchase_unique_index}
            ON account_move (company_id, partner_id, justech_do_ncf)
            WHERE state = 'posted'
              AND justech_do_ncf IS NOT NULL
              AND justech_do_ncf != ''
              AND COALESCE(justech_do_ncf_voided, false) = false
              AND move_type IN ('in_invoice', 'in_refund', 'in_receipt')
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
        # Motor fiscal: lecturas/escrituras técnicas con privilegios controlados.
        # El usuario de facturación no necesita ser gerente fiscal para publicar.
        self.env["justech.do.ncf.assignment.service"].sudo().with_context(
            justech_ncf_engine=True
        ).assign_before_post(self)

    def _justech_moves_for_ncf_on_post(self, soft=True):
        return self.env["justech.do.ncf.assignment.service"].moves_for_post(self, soft)

    def _justech_require_expense_type_before_post(self):
        for move in self.filtered(
            lambda m: m.move_type in ("in_invoice", "in_refund")
            and m.justech_do_include_in_dgii
        ):
            if not move.justech_do_expense_type_id and not (
                "l10n_do_expense_type" in move._fields and move.l10n_do_expense_type
            ):
                raise UserError(
                    _(
                        "Debe seleccionar el Tipo de costos y gastos antes de publicar "
                        "la factura de proveedor %(name)s (requerido para el 606)."
                    )
                    % {"name": move.display_name}
                )

    def _justech_validate_received_vendor_ncf_before_post(self):
        """Duplicidad/formato/consistencia del NCF recibido (LATAM), sin consumir rango."""
        fdp = self.env["justech.do.fiscal.data.provider"]
        for move in self.filtered(
            lambda m: m.move_type in ("in_invoice", "in_refund")
            and (m.justech_do_purchase_registration_mode or "received") == "received"
        ):
            ncf = (move.l10n_latam_document_number or "").strip()
            if not ncf:
                raise UserError(
                    _(
                        "Debe indicar el NCF del proveedor en %(name)s "
                        "(Documento recibido del proveedor)."
                    )
                    % {"name": move.display_name}
                )
            check = fdp.check_type_ncf_prefix_consistency(move)
            if not check["ok"]:
                raise UserError(
                    _(
                        "El tipo de comprobante seleccionado es %(tipo)s, pero el NCF "
                        "ingresado comienza con %(prefijo)s (%(ncf)s). Corrija el tipo "
                        "de comprobante o el NCF del proveedor antes de registrar la factura."
                    )
                    % {
                        "tipo": check["expected"],
                        "prefijo": check["found"],
                        "ncf": check["ncf"] or ncf,
                    }
                )
            move._justech_check_duplicate_ncf(ncf)

    def _justech_validate_type_ncf_prefix_before_post(self):
        """P0.1: bloquear publicación si tipo seleccionado ≠ prefijo del NCF efectivo.

        Aplica a ventas y compras emitidas (y refuerza recibidas). No modifica datos.
        No toca la baseline de alertas NCF.
        """
        Config = self.env["justech.do.fiscal.config.service"]
        fdp = self.env["justech.do.fiscal.data.provider"]
        for move in self.filtered(
            lambda m: m.move_type
            in ("out_invoice", "out_refund", "in_invoice", "in_refund")
        ):
            if not Config.is_fiscal_enabled(move.company_id):
                continue
            check = fdp.check_type_ncf_prefix_consistency(move)
            if check["ok"]:
                continue
            raise UserError(
                _(
                    "Inconsistencia fiscal en %(name)s: el tipo de comprobante "
                    "(%(tipo)s) no coincide con el prefijo del NCF (%(prefijo)s / %(ncf)s). "
                    "Corrija el tipo o el NCF antes de publicar."
                )
                % {
                    "name": move.display_name,
                    "tipo": check["expected"],
                    "prefijo": check["found"],
                    "ncf": check["ncf"] or "",
                }
            )

    def _post(self, soft=True):
        self._justech_require_expense_type_before_post()
        self._justech_validate_received_vendor_ncf_before_post()
        self._justech_moves_for_ncf_on_post(soft)._justech_assign_ncf_before_post()
        self._justech_validate_type_ncf_prefix_before_post()
        return super()._post(soft=soft)

    def action_post(self):
        return super().action_post()

    def _justech_get_issued_ncf(self):
        """NCF emitido efectivo (Justech o LATAM histórico). No inventa secuencias."""
        self.ensure_one()
        if self.justech_do_ncf:
            return (self.justech_do_ncf or "").strip()
        fdp = self.env["justech.do.fiscal.data.provider"]
        return (fdp.get_ncf(self) or "").strip()

    @api.depends(
        "justech_do_ncf",
        "justech_do_ncf_voided",
        "state",
        "l10n_latam_document_number",
    )
    def _compute_justech_do_can_void_ncf(self):
        for move in self:
            move.justech_do_can_void_ncf = bool(
                move.state == "posted"
                and not move.justech_do_ncf_voided
                and move._justech_get_issued_ncf()
            )

    def action_open_void_ncf_wizard(self):
        """Abre wizard modal para capturar motivo 608 antes de anular."""
        self.ensure_one()
        if self.justech_do_ncf_voided:
            raise UserError(_("Este comprobante fiscal ya fue anulado."))
        if self.state != "posted":
            raise UserError(_("Solo documentos publicados pueden anular el comprobante fiscal."))
        if not self._justech_get_issued_ncf():
            raise UserError(_("No hay comprobante fiscal para anular."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Anular comprobante fiscal"),
            "res_model": "justech.do.ncf.void.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_move_id": self.id,
                "dialog_size": "medium",
            },
        }

    def action_void_ncf(self):
        """Anulación fiscal del NCF (no cancela el asiento contable).

        Preferir `action_open_void_ncf_wizard`. Si se invoca directo, exige
        motivo ya cargado en el documento.
        """
        if not self.env.user.has_group(
            "justech_l10n_do_base.group_justech_do_fiscal_manager"
        ):
            raise AccessError(_("Solo los responsables fiscales pueden anular comprobantes."))
        Consumption = self.env["justech.do.ncf.consumption"]
        now = fields.Datetime.now()
        for move in self:
            if move.state != "posted":
                raise UserError(_("Solo documentos publicados pueden anular el comprobante fiscal."))
            issued_ncf = move._justech_get_issued_ncf()
            if not issued_ncf:
                raise UserError(_("No hay comprobante fiscal para anular."))
            if move.justech_do_ncf_voided:
                raise UserError(_("Este comprobante fiscal ya fue anulado."))
            reason = (move.justech_do_ncf_void_reason or "").strip()
            if not reason:
                raise UserError(
                    _(
                        "Debe indicar el motivo de anulación antes de anular "
                        "el comprobante fiscal."
                    )
                )
            if not move.justech_do_ncf_cancel_type:
                raise UserError(
                    _("Debe indicar el tipo de anulación DGII (catálogo 608).")
                )
            prev_state = move.state
            # Alinear campo Justech con NCF ya emitido (LATAM histórico) sin reinventar.
            vals = {
                "justech_do_ncf_voided": True,
                "justech_do_ncf_void_date": fields.Date.context_today(move),
                "justech_do_dgii_line_status": "2",
                "justech_do_dgii_fiscal_state": "cancelled",
                "justech_do_include_in_dgii": False,
            }
            if not move.justech_do_ncf:
                vals["justech_do_ncf"] = issued_ncf
            move.write(vals)
            consumption = Consumption.sudo().search(
                [
                    ("move_id", "=", move.id),
                    ("ncf", "=", issued_ncf),
                    ("state", "=", "consumed"),
                ],
                limit=1,
            )
            if consumption:
                # Escritura técnica de auditoría; el método ya exige fiscal manager.
                consumption.sudo().with_context(justech_ncf_engine=True).write(
                    {
                        "state": "voided",
                        "void_user_id": self.env.user.id,
                        "void_datetime": now,
                        "void_reason": reason,
                    }
                )
            # Una sola línea de chatter legible (sin HTML crudo).
            cancel_label = self.env.context.get("justech_void_cancel_label") or dict(
                move._fields["justech_do_ncf_cancel_type"]._description_selection(self.env)
            ).get(move.justech_do_ncf_cancel_type, move.justech_do_ncf_cancel_type)
            body = _(
                "NCF %(ncf)s anulado.\n"
                "Motivo: %(motivo)s.\n"
                "Procesado por: %(user)s.\n"
                "Fecha: %(fecha)s.\n"
                "Estado contable: %(prev)s → %(post)s (sin cancelar asiento)."
            ) % {
                "ncf": issued_ncf,
                "motivo": cancel_label,
                "user": self.env.user.display_name,
                "fecha": fields.Datetime.to_string(now),
                "prev": prev_state,
                "post": move.state,
            }
            if not self.env.context.get("justech_skip_void_chatter"):
                move.message_post(body=body)

    @api.constrains("justech_do_ncf", "company_id", "state")
    def _check_ncf_unique_constraint(self):
        for move in self.filtered(lambda m: m.justech_do_ncf and m.state == "posted"):
            move._justech_check_duplicate_ncf(move.justech_do_ncf)
