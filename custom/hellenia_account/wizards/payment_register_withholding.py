"""Retenciones RD por factura en account.payment.register."""
from __future__ import annotations

from odoo import Command, api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    hellenia_withholding_line_ids = fields.One2many(
        "hellenia.payment.withholding.line",
        "register_wizard_id",
        string="Retenciones de la factura",
    )
    hellenia_withholding_total = fields.Monetary(
        compute="_compute_hellenia_withholding_total",
        string="Total retenido",
        currency_field="currency_id",
    )

    @api.depends("hellenia_withholding_line_ids.amount")
    def _compute_hellenia_withholding_total(self):
        for wiz in self:
            wiz.hellenia_withholding_total = sum(wiz.hellenia_withholding_line_ids.mapped("amount"))

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        wh_lines = self.hellenia_withholding_line_ids
        wh_total = sum(wh_lines.mapped("amount"))
        if wh_total and vals.get("amount"):
            vals["amount"] = max(vals["amount"] - wh_total, 0.0)
            for wh in wh_lines:
                if not wh.account_id or not wh.amount:
                    continue
                sign = -1 if self.payment_type == "outbound" else 1
                vals.setdefault("write_off_line_vals", []).append(
                    {
                        "name": wh.label or (wh.catalog_id.name if wh.catalog_id else wh.tax_id.name),
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
        return vals
