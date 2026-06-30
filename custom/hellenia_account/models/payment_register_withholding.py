"""Retenciones RD en wizard account.payment.register."""
from __future__ import annotations

from odoo import Command, api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    hellenia_wh_isr_gov = fields.Boolean(string="Retención 5% Gobierno")
    hellenia_wh_itbis_30 = fields.Boolean(string="Retención ITBIS 30%")
    hellenia_wh_isr_10 = fields.Boolean(string="Retención proveedor informal 10%")
    hellenia_wh_itbis_75 = fields.Boolean(string="Retención ITBIS informal 75%")
    hellenia_withholding_line_ids = fields.One2many(
        "hellenia.payment.withholding.line", "register_wizard_id", string="Detalle retenciones"
    )
    hellenia_withholding_total = fields.Monetary(
        compute="_compute_hellenia_withholding_total", string="Total retenido", currency_field="currency_id"
    )

    @api.depends("hellenia_withholding_line_ids.amount")
    def _compute_hellenia_withholding_total(self):
        for wiz in self:
            wiz.hellenia_withholding_total = sum(wiz.hellenia_withholding_line_ids.mapped("amount"))

    @api.onchange(
        "hellenia_wh_isr_gov",
        "hellenia_wh_itbis_30",
        "hellenia_wh_isr_10",
        "hellenia_wh_itbis_75",
        "line_ids",
    )
    def _onchange_hellenia_withholdings(self):
        for wiz in self:
            wiz._hellenia_recompute_withholding_lines()

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wiz in wizards:
            if any(wiz[f] for f in (
                "hellenia_wh_isr_gov",
                "hellenia_wh_itbis_30",
                "hellenia_wh_isr_10",
                "hellenia_wh_itbis_75",
            )):
                wiz._hellenia_recompute_withholding_lines()
        return wizards

    def _hellenia_recompute_withholding_lines(self):
        specs = (
            ("hellenia_wh_isr_gov", "-5% ISR Gov.", "sale"),
            ("hellenia_wh_itbis_30", "-30% ITBIS Leg. (N02-05)", "purchase"),
            ("hellenia_wh_isr_10", "-10% ISR Fee", "purchase"),
            ("hellenia_wh_itbis_75", "-75% ITBIS (N08-10)", "purchase"),
        )
        Tax = self.env["account.tax"]
        for wiz in self:
            lines = [Command.clear()]
            moves = wiz.line_ids.mapped("move_id")
            for flag, name, use in specs:
                if not wiz[flag]:
                    continue
                tax = Tax.search(
                    [("name", "=", name), ("type_tax_use", "=", use), ("company_id", "=", wiz.company_id.id)],
                    limit=1,
                )
                if not tax:
                    continue
                for move in moves:
                    if use == "sale" and move.move_type not in ("out_invoice", "out_refund"):
                        continue
                    if use == "purchase" and move.move_type not in ("in_invoice", "in_refund"):
                        continue
                    base = move.amount_untaxed
                    amount = abs(tax.amount / 100.0 * base)
                    account = tax.invoice_repartition_line_ids.filtered(
                        lambda l: l.repartition_type == "tax"
                    )[:1].account_id
                    lines.append(
                        Command.create(
                            {
                                "register_wizard_id": wiz.id,
                                "tax_id": tax.id,
                                "label": name,
                                "base_amount": base,
                                "rate": tax.amount,
                                "amount": amount,
                                "account_id": account.id if account else False,
                                "currency_id": wiz.currency_id.id,
                            }
                        )
                    )
            wiz.hellenia_withholding_line_ids = lines

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        wh_total = sum(self.hellenia_withholding_line_ids.mapped("amount"))
        if wh_total and vals.get("amount"):
            vals["amount"] = max(vals["amount"] - wh_total, 0.0)
            for wh in self.hellenia_withholding_line_ids:
                if not wh.account_id or not wh.amount:
                    continue
                sign = -1 if self.payment_type == "outbound" else 1
                vals.setdefault("write_off_line_vals", []).append(
                    {
                        "name": wh.label or wh.tax_id.name,
                        "account_id": wh.account_id.id,
                        "partner_id": self.partner_id.id,
                        "currency_id": self.currency_id.id,
                        "amount_currency": sign * wh.amount,
                        "balance": self.currency_id._convert(
                            sign * wh.amount,
                            self.company_id.currency_id,
                            self.company_id,
                            self.payment_date,
                        ),
                    }
                )
            vals["payment_difference_handling"] = "reconcile"
        return vals
