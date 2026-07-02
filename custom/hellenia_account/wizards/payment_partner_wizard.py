"""Wizard cobro/pago — arquitectura nativa Odoo 19 Enterprise (Fase 20.1)."""
from __future__ import annotations

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HelleniaPaymentPartnerWizardLine(models.TransientModel):
    _name = "hellenia.payment.partner.wizard.line"
    _description = "Línea factura pendiente — wizard pago"

    wizard_id = fields.Many2one("hellenia.payment.partner.wizard", required=True, ondelete="cascade")
    move_id = fields.Many2one("account.move", required=True, ondelete="cascade")
    apply = fields.Boolean(string="Aplicar", default=False)
    invoice_name = fields.Char(related="move_id.name", string="Factura")
    ncf = fields.Char(related="move_id.justech_do_ncf", string="NCF")
    invoice_date = fields.Date(related="move_id.invoice_date", string="Fecha")
    date_maturity = fields.Date(compute="_compute_date_maturity", string="Vencimiento")
    currency_id = fields.Many2one(related="move_id.currency_id", string="Moneda")
    amount_total = fields.Monetary(related="move_id.amount_total", string="Total")
    amount_untaxed = fields.Monetary(related="move_id.amount_untaxed", string="Base imponible")
    amount_tax = fields.Monetary(related="move_id.amount_tax", string="ITBIS facturado")
    amount_residual = fields.Monetary(compute="_compute_amount_residual", string="Pendiente")
    amount_to_pay = fields.Monetary(string="Monto a aplicar", currency_field="currency_id", default=0.0)

    company_id = fields.Many2one(related="move_id.company_id", string="Compañía")
    move_scope_filter = fields.Selection(
        [("sale", "Venta"), ("purchase", "Compra")],
        compute="_compute_move_scope_filter",
        string="Operación factura",
    )
    withholding_catalog_ids = fields.Many2many(
        "hellenia.withholding.catalog",
        "hellenia_payment_wizard_line_wh_rel",
        "line_id",
        "catalog_id",
        string="Retenciones",
    )
    withholding_summary = fields.Char(compute="_compute_withholding_display", string="Resumen retenciones")
    withholding_amount = fields.Monetary(
        compute="_compute_withholding_display", string="Total retenido", currency_field="currency_id"
    )
    withholding_detail_ids = fields.One2many(
        "hellenia.payment.withholding.wizard.line", "wizard_line_id", string="Detalle retenciones"
    )
    net_after_withholding = fields.Monetary(
        compute="_compute_withholding_display", string="Neto a pagar/cobrar", currency_field="currency_id"
    )

    @api.depends("move_id", "move_id.move_type")
    def _compute_move_scope_filter(self):
        for line in self:
            if line.move_id.move_type in ("out_invoice", "out_refund"):
                line.move_scope_filter = "sale"
            else:
                line.move_scope_filter = "purchase"

    @api.depends("move_id")
    def _compute_date_maturity(self):
        for line in self:
            aml = line.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type in ("asset_receivable", "liability_payable")
            )[:1]
            line.date_maturity = aml.date_maturity if aml else line.move_id.invoice_date_due

    @api.depends("move_id", "move_id.amount_residual")
    def _compute_amount_residual(self):
        for line in self:
            line.amount_residual = abs(line.move_id.amount_residual)

    @api.depends("withholding_catalog_ids", "withholding_detail_ids.amount", "amount_to_pay", "apply", "currency_id")
    def _compute_withholding_display(self):
        for line in self:
            if not line.apply or not line.withholding_catalog_ids:
                line.withholding_summary = "Ninguna"
                line.withholding_amount = 0.0
                line.net_after_withholding = line.amount_to_pay if line.apply else 0.0
                continue
            labels = line.withholding_catalog_ids.mapped("name")
            line.withholding_summary = ", ".join(labels)
            partner_type = line._catalog_domain_partner_type()
            total = 0.0
            for catalog in line.withholding_catalog_ids:
                if not catalog._applies_to_move(line.move_id, partner_type):
                    continue
                total += catalog.compute_withholding_amount(
                    line.move_id, applied_amount=line.amount_to_pay
                )
            line.withholding_amount = total
            line.net_after_withholding = (line.amount_to_pay or 0.0) - total

    @api.constrains("apply", "amount_to_pay")
    def _check_apply_amount_to_pay(self):
        for line in self:
            if not line.apply and (line.amount_to_pay or 0.0) > 0.01:
                raise ValidationError(
                    f"La factura {line.move_id.name} no está seleccionada; "
                    "el monto a aplicar debe ser cero."
                )

    @api.onchange("apply")
    def _onchange_apply(self):
        """Sugerir residual solo cuando el usuario marca apply=True."""
        for line in self:
            if not line.apply:
                line.amount_to_pay = 0.0
                line.withholding_catalog_ids = [Command.clear()]
                line.withholding_detail_ids = [Command.clear()]
                continue
            if not line.amount_to_pay:
                line.amount_to_pay = line.amount_residual
            if line.withholding_catalog_ids:
                line._recompute_line_withholdings()

    @api.onchange("withholding_catalog_ids")
    def _onchange_withholding_catalog_ids(self):
        for line in self:
            if line.apply:
                line._recompute_line_withholdings()

    @api.onchange("amount_to_pay")
    def _onchange_amount_to_pay(self):
        for line in self:
            if not line.apply:
                line.amount_to_pay = 0.0
                continue
            if line.withholding_catalog_ids:
                line._recompute_line_withholdings()

    def _catalog_domain_partner_type(self):
        self.ensure_one()
        return self.wizard_id.partner_type if self.wizard_id else "customer"

    def _recompute_line_withholdings(self):
        for line in self:
            if not line.move_id or not line.apply:
                line.withholding_detail_ids = [Command.clear()]
                continue
            partner_type = line._catalog_domain_partner_type()
            details = [Command.clear()]
            for catalog in line.withholding_catalog_ids:
                if not catalog._applies_to_move(line.move_id, partner_type):
                    continue
                amount = catalog.compute_withholding_amount(
                    line.move_id, applied_amount=line.amount_to_pay
                )
                if not amount:
                    continue
                details.append(
                    Command.create(
                        {
                            "catalog_id": catalog.id,
                            "tax_id": catalog.tax_id.id,
                            "label": catalog.name,
                            "base_label": catalog._base_label(),
                            "base_amount": catalog._base_amount(
                                line.move_id, applied_amount=line.amount_to_pay
                            ),
                            "rate": catalog.rate,
                            "amount": amount,
                            "account_id": catalog.account_id.id,
                            "currency_id": line.currency_id.id,
                        }
                    )
                )
            line.withholding_detail_ids = details


class HelleniaPaymentPartnerWizard(models.TransientModel):
    _name = "hellenia.payment.partner.wizard"
    _description = "Registrar cobro o pago con facturas pendientes"

    partner_type = fields.Selection(
        [("customer", "Cliente"), ("supplier", "Proveedor")],
        required=True,
        default="customer",
    )
    partner_id = fields.Many2one("res.partner", string="Contacto", required=True)
    currency_id = fields.Many2one(
        "res.currency", string="Moneda", default=lambda self: self.env.company.currency_id
    )
    line_ids = fields.One2many("hellenia.payment.partner.wizard.line", "wizard_id", string="Facturas pendientes")
    journal_id = fields.Many2one("account.journal", domain="[('type', 'in', ('bank', 'cash'))]")
    payment_method_line_id = fields.Many2one("account.payment.method.line", string="Método de pago")
    payment_date = fields.Date(default=fields.Date.context_today, string="Fecha de pago")
    communication = fields.Char(string="Concepto de pago")

    withholding_line_ids = fields.One2many(
        "hellenia.payment.withholding.wizard.line",
        "wizard_id",
        string="Detalle retenciones",
        compute="_compute_withholding_lines",
    )
    withholding_total = fields.Monetary(compute="_compute_totals", string="Total retenido", currency_field="currency_id")
    payment_total = fields.Monetary(compute="_compute_totals", string="Total a pagar/cobrar", currency_field="currency_id")
    amount_after_withholding = fields.Monetary(
        compute="_compute_totals", string="Neto a transferir", currency_field="currency_id"
    )

    hellenia_payment_reference = fields.Char(string="Referencia")
    hellenia_card_auth = fields.Char(string="Autorización")
    hellenia_card_batch = fields.Char(string="Lote")
    hellenia_check_number = fields.Char(string="Número de cheque")
    hellenia_check_bank_id = fields.Many2one("res.bank", string="Banco del cheque")
    hellenia_check_date = fields.Date(string="Fecha del cheque")
    hellenia_show_card_fields = fields.Boolean(compute="_compute_method_flags")
    hellenia_show_check_fields = fields.Boolean(compute="_compute_method_flags")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner_type = self.env.context.get("default_partner_type") or res.get("partner_type") or "customer"
        res["partner_type"] = partner_type
        partner_id = self.env.context.get("default_partner_id") or res.get("partner_id")
        if not partner_id and self.env.context.get("active_model") == "res.partner":
            partner_id = self.env.context.get("active_id")
        if partner_id:
            res["partner_id"] = partner_id
        currency = self.env.company.currency_id
        if self.env.context.get("default_currency_id"):
            currency = self.env["res.currency"].browse(self.env.context["default_currency_id"])
        res.setdefault("currency_id", currency.id)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Respeta el estado enviado por la UI — sin recargar facturas."""
        return super().create(vals_list)

    @api.depends("line_ids.withholding_detail_ids")
    def _compute_withholding_lines(self):
        for wiz in self:
            wiz.withholding_line_ids = wiz.line_ids.mapped("withholding_detail_ids")

    @api.depends("payment_method_line_id.name")
    def _compute_method_flags(self):
        for wiz in self:
            name = (wiz.payment_method_line_id.name or "").lower()
            wiz.hellenia_show_card_fields = "tarjeta" in name
            wiz.hellenia_show_check_fields = "cheque" in name

    @api.depends("line_ids.amount_to_pay", "line_ids.apply", "line_ids.withholding_amount")
    def _compute_totals(self):
        for wiz in self:
            selected = wiz.line_ids.filtered("apply")
            wiz.payment_total = sum(selected.mapped("amount_to_pay"))
            wiz.withholding_total = sum(selected.mapped("withholding_amount"))
            wiz.amount_after_withholding = wiz.payment_total - wiz.withholding_total

    def _move_types(self):
        self.ensure_one()
        if self.partner_type == "customer":
            return ("out_invoice", "out_refund")
        return ("in_invoice", "in_refund")

    def _load_pending_invoices(self):
        """Único punto autorizado: onchange de partner. Líneas limpias."""
        self.ensure_one()
        if not self.partner_id:
            self.line_ids = [Command.clear()]
            return
        moves = self.env["account.move"].search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("move_type", "in", self._move_types()),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial")),
                ("company_id", "=", self.env.company.id),
            ],
            order="invoice_date asc, id asc",
        )
        if self.currency_id:
            moves = moves.filtered(lambda m: m.currency_id == self.currency_id)
        lines = [Command.clear()]
        for move in moves:
            lines.append(
                Command.create(
                    {
                        "move_id": move.id,
                        "apply": False,
                        "amount_to_pay": 0.0,
                    }
                )
            )
        self.line_ids = lines

    @api.onchange("partner_id", "partner_type", "currency_id")
    def _onchange_partner_load_invoices(self):
        self._load_pending_invoices()

    @api.onchange("payment_method_line_id")
    def _onchange_payment_method_journal(self):
        if self.payment_method_line_id and self.payment_method_line_id.journal_id:
            self.journal_id = self.payment_method_line_id.journal_id

    @api.onchange("currency_id", "partner_type")
    def _onchange_currency_journal(self):
        if not self.currency_id:
            return
        code = "BNKU" if self.currency_id.name == "USD" else "BNKD"
        if self.payment_method_line_id and "efectivo" in (self.payment_method_line_id.name or "").lower():
            code = "CSH1"
        journal = self.env["account.journal"].search(
            [("code", "=", code), ("company_id", "=", self.env.company.id)], limit=1
        )
        if journal:
            self.journal_id = journal
            lines = (
                journal.inbound_payment_method_line_ids
                if self.partner_type == "customer"
                else journal.outbound_payment_method_line_ids
            )
            transfer = lines.filtered(lambda l: "transferencia" in (l.name or "").lower())[:1]
            self.payment_method_line_id = transfer or lines[:1]

    @api.onchange("journal_id", "partner_type")
    def _onchange_journal_payment_method(self):
        if not self.journal_id:
            return
        lines = (
            self.journal_id.inbound_payment_method_line_ids
            if self.partner_type == "customer"
            else self.journal_id.outbound_payment_method_line_ids
        )
        if not self.payment_method_line_id or self.payment_method_line_id.journal_id != self.journal_id:
            transfer = lines.filtered(lambda l: "transferencia" in (l.name or "").lower())[:1]
            self.payment_method_line_id = transfer or lines[:1]

    def _register_vals_common(self):
        self.ensure_one()
        return {
            "journal_id": self.journal_id.id,
            "payment_method_line_id": self.payment_method_line_id.id,
            "payment_date": self.payment_date,
            "hellenia_payment_reference": self.hellenia_payment_reference,
            "hellenia_card_auth": self.hellenia_card_auth,
            "hellenia_card_batch": self.hellenia_card_batch,
            "hellenia_check_number": self.hellenia_check_number,
            "hellenia_check_bank_id": self.hellenia_check_bank_id.id,
            "hellenia_check_date": self.hellenia_check_date,
        }

    def _withholding_commands_for_line(self, line):
        line._recompute_line_withholdings()
        wh_total = sum(line.withholding_detail_ids.mapped("amount"))
        if wh_total and line.amount_to_pay < wh_total:
            raise UserError(
                f"La factura {line.move_id.name}: el monto retenido ({wh_total:.2f}) "
                f"supera el monto a aplicar ({line.amount_to_pay:.2f})."
            )
        commands = []
        for wh in line.withholding_detail_ids:
            if not wh.amount or not wh.account_id:
                continue
            commands.append(
                Command.create(
                    {
                        "wizard_line_id": line.id,
                        "catalog_id": wh.catalog_id.id,
                        "tax_id": wh.tax_id.id,
                        "label": wh.label,
                        "base_label": wh.base_label,
                        "base_amount": wh.base_amount,
                        "rate": wh.rate,
                        "amount": wh.amount,
                        "account_id": wh.account_id.id,
                        "currency_id": wh.currency_id.id,
                    }
                )
            )
        return commands

    def _validate_lines_for_register(self):
        self.ensure_one()
        self.env.flush_all()
        invalid_unselected = self.line_ids.filtered(lambda l: not l.apply and (l.amount_to_pay or 0.0) > 0.01)
        if invalid_unselected:
            names = ", ".join(invalid_unselected.mapped("move_id.name"))
            raise UserError(
                f"Facturas no seleccionadas con monto distinto de cero: {names}. "
                "Desmarque o ponga el monto en cero."
            )
        selected = self.line_ids.filtered(lambda l: l.apply and (l.amount_to_pay or 0.0) > 0)
        if not selected:
            raise UserError("Debe seleccionar al menos una factura con un monto mayor que cero.")
        for line in selected:
            residual = abs(line.move_id.amount_residual)
            if line.amount_to_pay > residual + 0.01:
                raise UserError(
                    f"El monto a aplicar ({line.amount_to_pay:.2f}) supera el pendiente "
                    f"de {line.move_id.name} ({residual:.2f})."
                )
        return selected

    def _register_vals_for_line(self, line, common):
        move = line.move_id
        applied = line.amount_to_pay
        residual = abs(move.amount_residual)
        is_partial = applied < residual - 0.01
        register_vals = {
            **common,
            "communication": self.communication or move.name,
            "amount": applied,
            "hellenia_withholding_line_ids": self._withholding_commands_for_line(line),
        }
        if is_partial:
            register_vals.update(
                {
                    "custom_user_amount": applied,
                    "custom_user_currency_id": line.currency_id.id,
                    "payment_difference_handling": "open",
                }
            )
        return register_vals, applied, is_partial

    def action_register_payments(self):
        self.ensure_one()
        if not self.journal_id or not self.payment_method_line_id:
            raise UserError("Indique diario y método de pago.")
        if not self.partner_id:
            raise UserError("Indique el contacto.")

        selected = self._validate_lines_for_register()
        if self.withholding_total and self.amount_after_withholding < 0:
            raise UserError("El total retenido supera el monto a aplicar.")

        payments = self.env["account.payment"]
        common = self._register_vals_common()
        Register = self.env["account.payment.register"]

        for line in selected:
            move = line.move_id
            register_vals, applied, is_partial = self._register_vals_for_line(line, common)
            register_ctx = {
                "active_model": "account.move",
                "active_ids": [move.id],
                "dont_redirect_to_payments": True,
                "hellenia_applied_amount": applied,
                "hellenia_single_invoice_id": move.id,
            }
            if is_partial:
                register_ctx["force_payment_move"] = True
            register = Register.with_context(**register_ctx).create(register_vals)
            if is_partial or register.currency_id.compare_amounts(register.amount, applied) != 0:
                register.write(
                    {
                        "amount": applied,
                        "custom_user_amount": applied,
                        "custom_user_currency_id": line.currency_id.id,
                        "payment_difference_handling": "open",
                    }
                )
            create_ctx = {"force_payment_move": True} if is_partial else {}
            created = register.with_context(**create_ctx)._create_payments()
            if len(created) != 1:
                raise UserError(
                    f"Se esperaba un pago para {move.name}; se crearon {len(created)}."
                )
            payments |= created

        if len(payments) != len(selected):
            raise UserError(
                f"Se crearon {len(payments)} pagos para {len(selected)} factura(s) seleccionada(s)."
            )

        return {
            "type": "ir.actions.act_window",
            "name": "Pagos registrados",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", payments.ids)],
        }
