"""Wizard cobro/pago desde Clientes/Proveedores → Pagos."""
from __future__ import annotations

from odoo import Command, api, fields, models
from odoo.exceptions import UserError


WITHHOLDING_SPECS = (
    ("wh_isr_gov", "-5% ISR Gov.", "sale", "Gobierno 5%"),
    ("wh_itbis_30", "-30% ITBIS Leg. (N02-05)", "purchase", "ITBIS retenido 30%"),
    ("wh_isr_10", "-10% ISR Fee", "purchase", "Proveedor informal 10%"),
    ("wh_itbis_75", "-75% ITBIS (N08-10)", "purchase", "ITBIS informal 75%"),
)


class HelleniaPaymentPartnerWizardLine(models.TransientModel):
    _name = "hellenia.payment.partner.wizard.line"
    _description = "Línea factura pendiente — wizard pago"

    wizard_id = fields.Many2one("hellenia.payment.partner.wizard", required=True, ondelete="cascade")
    move_id = fields.Many2one("account.move", required=True, ondelete="cascade")
    apply = fields.Boolean(string="Aplicar", default=True)
    invoice_name = fields.Char(related="move_id.name", string="Factura")
    ncf = fields.Char(related="move_id.justech_do_ncf", string="NCF")
    invoice_date = fields.Date(related="move_id.invoice_date", string="Fecha")
    date_maturity = fields.Date(compute="_compute_date_maturity", string="Vencimiento")
    currency_id = fields.Many2one(related="move_id.currency_id", string="Moneda")
    amount_total = fields.Monetary(related="move_id.amount_total", string="Total")
    amount_residual = fields.Monetary(compute="_compute_amount_residual", string="Pendiente")
    amount_to_pay = fields.Monetary(string="Monto a aplicar", currency_field="currency_id")

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

    @api.onchange("apply", "amount_residual")
    def _onchange_apply(self):
        for line in self:
            if line.apply and not line.amount_to_pay:
                line.amount_to_pay = line.amount_residual


class HelleniaPaymentWithholdingLine(models.TransientModel):
    _name = "hellenia.payment.withholding.line"
    _description = "Detalle retención — wizard pago"

    wizard_id = fields.Many2one("hellenia.payment.partner.wizard", ondelete="cascade")
    register_wizard_id = fields.Many2one("account.payment.register", ondelete="cascade")
    tax_id = fields.Many2one("account.tax", string="Retención")
    label = fields.Char(string="Descripción")
    base_amount = fields.Monetary(string="Base", currency_field="currency_id")
    rate = fields.Float(string="Porcentaje")
    amount = fields.Monetary(string="Monto retenido", currency_field="currency_id")
    account_id = fields.Many2one("account.account", string="Cuenta contable")
    currency_id = fields.Many2one("res.currency", string="Moneda")


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
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many("hellenia.payment.partner.wizard.line", "wizard_id", string="Facturas pendientes")
    journal_id = fields.Many2one("account.journal", domain="[('type', 'in', ('bank', 'cash'))]")
    payment_method_line_id = fields.Many2one("account.payment.method.line", string="Método de pago")
    payment_date = fields.Date(default=fields.Date.context_today, string="Fecha de pago")
    communication = fields.Char(string="Concepto de pago")

    wh_isr_gov = fields.Boolean(string="Retención 5% Gobierno")
    wh_itbis_30 = fields.Boolean(string="Retención ITBIS 30%")
    wh_isr_10 = fields.Boolean(string="Retención proveedor informal 10%")
    wh_itbis_75 = fields.Boolean(string="Retención ITBIS informal 75%")

    withholding_line_ids = fields.One2many("hellenia.payment.withholding.line", "wizard_id", string="Detalle retenciones")
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
    hellenia_show_customer_withholdings = fields.Boolean(compute="_compute_withholding_visibility")
    hellenia_show_supplier_withholdings = fields.Boolean(compute="_compute_withholding_visibility")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner_type = self.env.context.get("default_partner_type") or res.get("partner_type") or "customer"
        res["partner_type"] = partner_type
        partner_id = (
            self.env.context.get("default_partner_id")
            or res.get("partner_id")
            or self.env.context.get("active_id")
            if self.env.context.get("active_model") == "res.partner"
            else False
        )
        if partner_id:
            res["partner_id"] = partner_id
        currency = self.env.company.currency_id
        if self.env.context.get("default_currency_id"):
            currency = self.env["res.currency"].browse(self.env.context["default_currency_id"])
        res.setdefault("currency_id", currency.id)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wiz in wizards:
            if wiz.partner_id:
                wiz._load_pending_invoices()
                wiz._recompute_withholdings()
        return wizards

    @api.depends("partner_type")
    def _compute_withholding_visibility(self):
        for wiz in self:
            wiz.hellenia_show_customer_withholdings = wiz.partner_type == "customer"
            wiz.hellenia_show_supplier_withholdings = wiz.partner_type == "supplier"

    @api.depends("payment_method_line_id.name")
    def _compute_method_flags(self):
        for wiz in self:
            name = (wiz.payment_method_line_id.name or "").lower()
            wiz.hellenia_show_card_fields = "tarjeta" in name
            wiz.hellenia_show_check_fields = "cheque" in name

    @api.depends("line_ids.amount_to_pay", "line_ids.apply", "withholding_line_ids.amount")
    def _compute_totals(self):
        for wiz in self:
            selected = wiz.line_ids.filtered("apply")
            wiz.payment_total = sum(selected.mapped("amount_to_pay"))
            wiz.withholding_total = sum(wiz.withholding_line_ids.mapped("amount"))
            wiz.amount_after_withholding = wiz.payment_total - wiz.withholding_total

    def _move_types(self):
        self.ensure_one()
        if self.partner_type == "customer":
            return ("out_invoice", "out_refund")
        return ("in_invoice", "in_refund")

    def _load_pending_invoices(self):
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
                        "apply": True,
                        "amount_to_pay": abs(move.amount_residual),
                    }
                )
            )
        self.line_ids = lines

    @api.onchange("partner_id", "partner_type", "currency_id")
    def _onchange_partner_load_invoices(self):
        self._load_pending_invoices()
        self._recompute_withholdings()

    @api.onchange("wh_isr_gov", "wh_itbis_30", "wh_isr_10", "wh_itbis_75", "line_ids")
    def _onchange_withholdings(self):
        self._recompute_withholdings()

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

    def _get_tax(self, name, tax_use):
        return self.env["account.tax"].search(
            [("name", "=", name), ("type_tax_use", "=", tax_use), ("company_id", "=", self.env.company.id)],
            limit=1,
        )

    def _recompute_withholdings(self):
        for wiz in self:
            wh_lines = [Command.clear()]
            selected_moves = wiz.line_ids.filtered("apply").mapped("move_id")
            flags = {
                "wh_isr_gov": wiz.wh_isr_gov,
                "wh_itbis_30": wiz.wh_itbis_30,
                "wh_isr_10": wiz.wh_isr_10,
                "wh_itbis_75": wiz.wh_itbis_75,
            }
            for field_name, tax_name, tax_use, label in WITHHOLDING_SPECS:
                if not flags.get(field_name):
                    continue
                tax = wiz._get_tax(tax_name, tax_use)
                if not tax:
                    continue
                for move in selected_moves:
                    if tax_use == "sale" and move.move_type not in ("out_invoice", "out_refund"):
                        continue
                    if tax_use == "purchase" and move.move_type not in ("in_invoice", "in_refund"):
                        continue
                    base = move.amount_untaxed
                    amount = abs(tax.amount / 100.0 * base) if tax.amount_type == "percent" else 0.0
                    account = tax.invoice_repartition_line_ids.filtered(
                        lambda l: l.repartition_type == "tax"
                    )[:1].account_id
                    wh_lines.append(
                        Command.create(
                            {
                                "tax_id": tax.id,
                                "label": label,
                                "base_amount": base,
                                "rate": tax.amount,
                                "amount": amount,
                                "account_id": account.id if account else False,
                                "currency_id": wiz.currency_id.id,
                            }
                        )
                    )
            wiz.withholding_line_ids = wh_lines

    def action_register_payments(self):
        self.ensure_one()
        selected = self.line_ids.filtered(lambda l: l.apply and l.amount_to_pay > 0)
        if not selected:
            raise UserError("Seleccione al menos una factura con monto a aplicar.")
        if not self.journal_id or not self.payment_method_line_id:
            raise UserError("Indique diario y método de pago.")
        if self.withholding_total and self.amount_after_withholding < 0:
            raise UserError("El total retenido supera el monto a aplicar.")

        payments = self.env["account.payment"]
        for line in selected:
            move = line.move_id
            register = (
                self.env["account.payment.register"]
                .with_context(active_model="account.move", active_ids=move.ids, dont_redirect_to_payments=True)
                .create(
                    {
                        "journal_id": self.journal_id.id,
                        "payment_method_line_id": self.payment_method_line_id.id,
                        "payment_date": self.payment_date,
                        "communication": self.communication or move.name,
                        "amount": line.amount_to_pay,
                        "hellenia_payment_reference": self.hellenia_payment_reference,
                        "hellenia_card_auth": self.hellenia_card_auth,
                        "hellenia_card_batch": self.hellenia_card_batch,
                        "hellenia_check_number": self.hellenia_check_number,
                        "hellenia_check_bank_id": self.hellenia_check_bank_id.id,
                        "hellenia_check_date": self.hellenia_check_date,
                        "hellenia_wh_isr_gov": self.wh_isr_gov,
                        "hellenia_wh_itbis_30": self.wh_itbis_30,
                        "hellenia_wh_isr_10": self.wh_isr_10,
                        "hellenia_wh_itbis_75": self.wh_itbis_75,
                    }
                )
            )
            payments |= register._create_payments()

        return {
            "type": "ir.actions.act_window",
            "name": "Pagos registrados",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", payments.ids)],
        }
