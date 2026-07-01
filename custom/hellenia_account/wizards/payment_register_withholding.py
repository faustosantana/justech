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

    def _hellenia_invoice_for_batch(self, batch_result):
        move = self.env["account.move"]
        if batch_result and batch_result.get("lines"):
            move = batch_result["lines"].move_id[:1]
        if not move and self.line_ids:
            move = self.line_ids.move_id[:1]
        return move

    def _hellenia_persistent_withholding_commands(self, batch_result):
        move = self._hellenia_invoice_for_batch(batch_result)
        commands = []
        for wh in self.hellenia_withholding_line_ids:
            if not wh.amount:
                continue
            commands.append(
                Command.create(
                    {
                        "move_id": move.id if move else False,
                        "invoice_name": move.name if move else "",
                        "ncf": getattr(move, "justech_do_ncf", "") or "",
                        "catalog_id": wh.catalog_id.id,
                        "label": wh.label or (wh.catalog_id.name if wh.catalog_id else wh.tax_id.name),
                        "base_label": wh.base_label,
                        "base_amount": wh.base_amount,
                        "rate": wh.rate,
                        "amount": wh.amount,
                        "account_id": wh.account_id.id,
                    }
                )
            )
        return commands

    def _create_payment_vals_from_wizard(self, batch_result):
        applied_amount = self.amount
        vals = super()._create_payment_vals_from_wizard(batch_result)
        wh_lines = self.hellenia_withholding_line_ids
        wh_total = sum(wh_lines.mapped("amount"))
        if applied_amount:
            vals["hellenia_applied_amount"] = applied_amount
        if wh_total and vals.get("amount") is not None:
            vals["hellenia_withholding_line_ids"] = self._hellenia_persistent_withholding_commands(
                batch_result
            )
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

    def _create_payments(self):
        payments = super()._create_payments()
        payments._hellenia_link_withholding_move_lines()
        return payments
